"""Parse food nutrition from an arbitrary webpage for the manual-add importer.

Fetches a user-supplied URL server-side (SSRF-guarded) and extracts schema.org
nutrition — primarily a Recipe's ``NutritionInformation`` JSON-LD block, which
most recipe and many product pages embed — into ``ParsedFoodNutrition`` so the
web manual-add form can prefill its inputs. No AI: structured data only; pages
without it get a clean 422.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
import socket
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.schemas.food import ParsedFoodNutrition

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 6.0
# Overall wall-clock budget across all redirect hops, so a slowloris-style server
# that trickles bytes inside each per-op timeout can't hold the request open.
OVERALL_TIMEOUT_SECONDS = 12.0
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 3
USER_AGENT = "gym-app/0.1 (+https://github.com/anthropics/claude-code)"

_NUM = re.compile(r"-?\d[\d,]*\.?\d*")
# A gram weight inside a serving string like "1 cup (240 g)" or "240g".
_GRAMS = re.compile(r"(\d[\d.]*)\s*g\b", re.IGNORECASE)


def _blocked_ip(ip_text: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _validate_url(url: str) -> None:
    """Reject non-http(s) URLs and hosts that resolve to private/loopback ranges
    (SSRF guard). Raises HTTPException(400) when unsafe."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Enter a valid http(s) URL.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise HTTPException(status_code=400, detail="Could not resolve that URL.") from exc
    if any(_blocked_ip(str(info[4][0])) for info in infos):
        raise HTTPException(status_code=400, detail="That URL is not allowed.")


async def _fetch_html(url: str) -> str:
    """Fetch a page with SSRF validation on every redirect hop and a byte cap."""
    current = url
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _validate_url(current)
            try:
                async with client.stream(
                    "GET", current, headers={"User-Agent": USER_AGENT}
                ) as response:
                    if response.is_redirect and response.headers.get("location"):
                        current = urljoin(current, response.headers["location"])
                        continue
                    response.raise_for_status()
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_BYTES:
                            break
                        chunks.append(chunk)
                    return b"".join(chunks).decode("utf-8", errors="ignore")
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail="Couldn't fetch that page.") from exc
    raise HTTPException(status_code=400, detail="Too many redirects.")


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value)
    match = _NUM.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(0).replace(",", "")).quantize(Decimal("0.01"))
    except Exception:
        return None


def _iter_jsonld(soup: BeautifulSoup) -> list[Any]:
    """Yield every parsed JSON-LD object (flattening arrays and @graph)."""
    out: list[Any] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                out.append(node)
                if isinstance(node.get("@graph"), list):
                    stack.extend(node["@graph"])
    return out


def _has_type(node: dict[str, Any], wanted: str) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return any(str(t).lower() == wanted for t in node_type)
    return str(node_type).lower() == wanted


def _extract(html: str, source_url: str) -> ParsedFoodNutrition | None:
    soup = BeautifulSoup(html, "html.parser")
    nodes = _iter_jsonld(soup)

    nutrition: dict[str, Any] | None = None
    name: str | None = None
    # Prefer a Recipe (carries name + nutrition); fall back to a bare NutritionInformation.
    for node in nodes:
        if _has_type(node, "recipe") and isinstance(node.get("nutrition"), dict):
            nutrition = node["nutrition"]
            raw_name = node.get("name")
            name = str(raw_name)[:240] if raw_name else None
            break
    if nutrition is None:
        for node in nodes:
            if _has_type(node, "nutritioninformation"):
                nutrition = node
                break
    if name is None:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            name = str(og["content"])[:240]
        elif soup.title and soup.title.string:
            name = soup.title.string.strip()[:240]

    if nutrition is None:
        return None

    serving_label = nutrition.get("servingSize")
    serving_label = str(serving_label)[:240] if serving_label else None
    serving_grams: Decimal | None = None
    if serving_label:
        grams_match = _GRAMS.search(serving_label)
        if grams_match:
            serving_grams = _to_decimal(grams_match.group(1))

    parsed = ParsedFoodNutrition(
        name=name,
        serving_label=serving_label,
        serving_grams=serving_grams,
        kcal=_to_decimal(nutrition.get("calories")),
        protein_g=_to_decimal(nutrition.get("proteinContent")),
        carbs_g=_to_decimal(nutrition.get("carbohydrateContent")),
        fat_g=_to_decimal(nutrition.get("fatContent")),
        fiber_g=_to_decimal(nutrition.get("fiberContent")),
        source_url=source_url,
    )
    # Need at least one macro to be useful.
    if not any((parsed.kcal, parsed.protein_g, parsed.carbs_g, parsed.fat_g)):
        return None
    if serving_grams is None:
        parsed.warning = (
            "Couldn't read the serving size in grams — the macros are per serving; "
            "set the amount to match."
        )
    return parsed


async def parse_food_url(url: str) -> ParsedFoodNutrition:
    """Fetch + parse nutrition from ``url``. Raises HTTPException on failure."""
    cleaned = url.strip()
    try:
        async with asyncio.timeout(OVERALL_TIMEOUT_SECONDS):
            html = await _fetch_html(cleaned)
    except TimeoutError as exc:
        raise HTTPException(status_code=502, detail="That page took too long to load.") from exc
    parsed = _extract(html, cleaned)
    if parsed is None:
        raise HTTPException(
            status_code=422,
            detail="Couldn't find nutrition info on that page. Try a recipe or product page.",
        )
    return parsed
