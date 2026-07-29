#!/usr/bin/env python3
"""Refresh public product facts while preserving synthetic COGS assumptions."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "addons" / "sun_people_demo" / "data" / "catalog_snapshot.json"
ENDPOINT = "https://www.thesunpeople.com/collections/shop/products.json?limit=250"


def main() -> None:
    current = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    costs_by_name = {
        item["name"]: item["unit_cogs"] for item in current["products"]
    }
    request = Request(ENDPOINT, headers={"User-Agent": "sun-people-odoo-demo/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    refreshed = []
    for product in payload["products"]:
        available_variants = [
            variant for variant in product["variants"] if variant.get("available", True)
        ]
        if not available_variants:
            continue
        variant = available_variants[0]
        name = product["title"]
        if name not in costs_by_name:
            raise RuntimeError(
                f"New or renamed product {name!r}; add a reviewed unit_cogs assumption first."
            )
        item = {
            "sku": variant.get("sku") or product["handle"].upper(),
            "name": name,
            "sale_price": float(Decimal(variant["price"])),
            "source_status": "current",
            "unit_cogs": costs_by_name[name],
        }
        if variant.get("compare_at_price"):
            item["compare_at_price"] = float(Decimal(variant["compare_at_price"]))
            item["source_status"] = "current_sale"
        refreshed.append(item)

    current["retrieved_at"] = date.today().isoformat()
    current["products"] = refreshed
    SNAPSHOT.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(f"Refreshed {len(refreshed)} products in {SNAPSHOT.relative_to(ROOT)}")
    print("Run `make generate-orders check` to rebuild and validate the fixture.")


if __name__ == "__main__":
    main()
