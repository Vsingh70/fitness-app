"""Smoke-test the FatSecret integration against the live API.

Run from apps/api with the credentials present in the environment (e.g. in
apps/api/.env as FATSECRET_CLIENT_ID / FATSECRET_CLIENT_SECRET):

    uv run python -m scripts.verify_fatsecret

It fetches an OAuth token, runs a text search, pulls full detail (servings),
and tries a barcode lookup. It prints diagnostics only, never the credentials.

IMPORTANT: FatSecret's basic tier only answers from allowlisted server IPs. If
you run this locally, this machine's public IP must be on the FatSecret
allowlist, otherwise the calls fail with an IP / permission error.
"""

import asyncio

from app.clients import fatsecret
from app.config import get_settings

KNOWN_BARCODE = "049000028904"  # Coca-Cola 12 oz can (UPC-A); best-effort.


async def _run() -> int:
    settings = get_settings()
    if not settings.fatsecret_client_id or not settings.fatsecret_client_secret:
        print("FAIL: FATSECRET_CLIENT_ID / FATSECRET_CLIENT_SECRET are not set.")
        print("      Add them to apps/api/.env (or export them) and re-run.")
        return 1

    print(f"creds present (client_id ...{settings.fatsecret_client_id[-4:]}); calling FatSecret...")

    # 1) token + text search
    try:
        hits = await fatsecret.search_foods("chicken breast", max_results=5)
    except fatsecret.FatSecretConfigError as exc:
        print(f"FAIL (config): {exc}")
        return 1
    except fatsecret.FatSecretAuthError as exc:
        print(f"FAIL (auth): {exc}")
        print("      -> client id/secret rejected at the token endpoint. Check the creds.")
        return 1
    except fatsecret.FatSecretClientError as exc:
        print(f"FAIL (api error): {exc}")
        print("      -> if this mentions IP / not allowed, this machine's public IP is not")
        print("         on the FatSecret server allowlist. Add it and retry.")
        return 1

    print(f"OK  search 'chicken breast' -> {len(hits)} hits")
    if not hits:
        print("    (no hits - unexpected for this query; the key may lack search scope)")
        return 1
    for h in hits[:3]:
        print(f"      - {h.name}{f' [{h.brand}]' if h.brand else ''} (id={h.food_id})")

    # 2) full detail with servings
    try:
        food = await fatsecret.get_food(hits[0].food_id)
    except fatsecret.FatSecretClientError as exc:
        print(f"FAIL (food.get): {exc}")
        return 1
    print(
        f"OK  detail '{food.name}' -> {food.kcal_per_100g} kcal/100g, {len(food.servings)} servings"
    )
    for s in food.servings[:4]:
        print(f"      - {s.description}: {s.grams} g")
    if not any(s.grams for s in food.servings):
        print("    WARN: no serving resolved a gram weight (downstream amounts need this)")

    # 3) barcode (may require the 'barcode' scope / premier tier)
    try:
        bc = await fatsecret.lookup_barcode(KNOWN_BARCODE)
        print(f"OK  barcode {KNOWN_BARCODE} -> {bc.name}")
    except fatsecret.FatSecretMethodNotAllowedError:
        print(
            f"SKIP barcode {KNOWN_BARCODE}: method not allowed on this key (needs barcode scope)."
        )
    except fatsecret.FatSecretNotFoundError:
        print(f"SKIP barcode {KNOWN_BARCODE}: no match (OFF fallback would handle this in-app).")
    except fatsecret.FatSecretClientError as exc:
        print(f"WARN barcode {KNOWN_BARCODE}: {exc}")

    print("\nDONE: FatSecret search + detail are working from this host.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
