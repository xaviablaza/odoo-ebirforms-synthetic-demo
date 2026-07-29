#!/usr/bin/env python3
"""Generate the deterministic FY2025 synthetic order fixture."""

from __future__ import annotations

import csv
import json
import random
from calendar import monthrange
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "addons" / "sun_people_demo" / "data"
OUTPUT = DATA_DIR / "synthetic_orders.csv"

CUSTOMERS = [
    "Demo Customer Aurora",
    "Demo Customer Bayani",
    "Demo Customer Coral",
    "Demo Customer Dalisay",
    "Demo Customer Estrella",
    "Demo Customer Flores",
    "Demo Customer Ginto",
    "Demo Customer Hiraya",
    "Demo Customer Isla",
    "Demo Customer Jasmin",
    "Demo Customer Kidlat",
    "Demo Customer Luntian",
]


def load_json(name: str) -> dict:
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    assumptions = load_json("assumptions.json")
    catalog = load_json("catalog_snapshot.json")
    sales = assumptions["sales"]
    products = catalog["products"]
    rng = random.Random(sales["random_seed"])
    cities = list(sales["lalamove_zone_rates"])

    rows = []
    sequence = 1
    for month in range(1, 13):
        last_day = monthrange(assumptions["demo_year"], month)[1]
        for index in range(sales["orders_per_month"]):
            day = 2 + ((index * 3 + month) % (last_day - 2))
            order_date = date(assumptions["demo_year"], month, day)
            chosen_count = (1, 2, 2, 3)[(index + month) % 4]
            chosen = rng.sample(products, k=chosen_count)
            quantities = {product["sku"]: 0 for product in products}
            for product in chosen:
                quantities[product["sku"]] = rng.randint(2, 7)

            product_subtotal = sum(
                quantities[product["sku"]] * product["sale_price"]
                for product in products
            )
            shipping_charge = (
                0.0
                if product_subtotal >= sales["free_shipping_threshold"]
                else sales["customer_shipping_charge_below_threshold"]
            )
            city = cities[(sequence + month) % len(cities)]
            rows.append(
                {
                    "order_id": f"TSP-{assumptions['demo_year']}-{sequence:04d}",
                    "order_date": order_date.isoformat(),
                    "customer": CUSTOMERS[(sequence + month) % len(CUSTOMERS)],
                    "city": city,
                    **quantities,
                    "product_subtotal": f"{product_subtotal:.2f}",
                    "shipping_charge": f"{shipping_charge:.2f}",
                    "lalamove_cost": f"{sales['lalamove_zone_rates'][city]:.2f}",
                }
            )
            sequence += 1

    fieldnames = [
        "order_id",
        "order_date",
        "customer",
        "city",
        *(product["sku"] for product in products),
        "product_subtotal",
        "shipping_charge",
        "lalamove_cost",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} deterministic orders to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
