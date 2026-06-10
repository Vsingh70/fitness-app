#!/usr/bin/env python3
"""Dependency-free FatSecret smoke-test, runnable on the API host.

Pure stdlib (no app code, no venv needed). Confirms the host's IP is on the
FatSecret allowlist and the client id/secret are valid, by fetching an OAuth
token and running a food search + detail. Prints diagnostics only, never the
credentials.

This targets the BASIC tier (foods.search v1 + food.get v2, scope 'basic'),
since premier/barcode scopes are not entitled on the current key.

Creds are read from the environment, falling back to /etc/gymapp/app.env.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
API_URL = "https://platform.fatsecret.com/rest/server.api"
ENV_FILE = os.environ.get("APP_ENV_FILE", "/etc/gymapp/app.env")


def _load_creds() -> tuple[str | None, str | None]:
    cid = os.environ.get("FATSECRET_CLIENT_ID")
    csec = os.environ.get("FATSECRET_CLIENT_SECRET")
    if cid and csec:
        return cid, csec
    try:
        with open(ENV_FILE) as f:
            env: dict[str, str] = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k] = v
        return env.get("FATSECRET_CLIENT_ID") or cid, env.get("FATSECRET_CLIENT_SECRET") or csec
    except OSError:
        return cid, csec


def _post(url: str, data: dict, headers: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode())


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def main() -> int:
    cid, csec = _load_creds()
    if not cid or not csec:
        print(f"FAIL: FATSECRET_CLIENT_ID/SECRET not in env or {ENV_FILE}.")
        return 1
    print(f"creds present (client_id ...{cid[-4:]}); fetching basic-scope token...")

    # 1) OAuth token (basic scope)
    try:
        basic = base64.b64encode(f"{cid}:{csec}".encode()).decode()
        tok = _post(
            TOKEN_URL,
            {"grant_type": "client_credentials", "scope": "basic"},
            {"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"},
        )
    except urllib.error.HTTPError as exc:
        print(f"FAIL token: HTTP {exc.code} {exc.read().decode()[:300]}")
        return 1
    token = tok.get("access_token")
    if not token:
        print(f"FAIL token: {tok}")
        return 1
    print("OK   token acquired (scope=basic)")

    # 2) foods.search (v1)
    try:
        res = _post(
            API_URL,
            {
                "method": "foods.search",
                "format": "json",
                "search_expression": "chicken breast",
                "max_results": 5,
            },
            {"Authorization": "Bearer " + token},
        )
    except urllib.error.HTTPError as exc:
        print(f"FAIL search: HTTP {exc.code} {exc.read().decode()[:300]}")
        return 1
    if "error" in res:
        err = res["error"]
        print(f"FAIL FatSecret error: {err}")
        msg = json.dumps(err).lower()
        if "ip" in msg or "not allowed" in msg or err.get("code") == 21:
            print("      -> host IP not on the FatSecret allowlist.")
        return 1

    foods = res.get("foods") or {}
    hits = _as_list(foods.get("food"))
    print(f"OK   foods.search 'chicken breast' -> {len(hits)} hits")
    for f in hits[:3]:
        print(f"       - {f.get('food_name')} [{f.get('food_type')}] (id={f.get('food_id')})")
    if not hits:
        print("     (no hits - unexpected)")
        return 1

    # 3) food.get.v2 detail (servings)
    try:
        det = _post(
            API_URL,
            {"method": "food.get.v2", "format": "json", "food_id": hits[0]["food_id"]},
            {"Authorization": "Bearer " + token},
        )
    except urllib.error.HTTPError as exc:
        print(f"FAIL food.get.v2: HTTP {exc.code} {exc.read().decode()[:300]}")
        return 1
    if "error" in det:
        print(f"FAIL food.get.v2 error: {det['error']}")
        return 1
    food = det.get("food") or {}
    servings = _as_list((food.get("servings") or {}).get("serving"))
    print(f"OK   food.get.v2 '{food.get('food_name')}' -> {len(servings)} servings")
    for s in servings[:4]:
        amt = s.get("metric_serving_amount")
        unit = s.get("metric_serving_unit")
        print(f"       - {s.get('serving_description')}: {amt} {unit}, {s.get('calories')} kcal")
    if not any(s.get("metric_serving_amount") for s in servings):
        print("     WARN: no serving exposed a metric gram amount")

    print("\nDONE: basic-tier foods.search + food.get.v2 work with this key and host IP.")
    print("      (barcode needs the premier 'barcode' scope; app falls back to Open Food Facts.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
