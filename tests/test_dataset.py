from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "addons" / "sun_people_demo" / "data"


def load_json(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load_orders():
    with (DATA_DIR / "synthetic_orders.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


class DatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assumptions = load_json("assumptions.json")
        cls.catalog = load_json("catalog_snapshot.json")
        cls.orders = load_orders()

    def test_public_catalog_snapshot(self):
        prices = {
            item["sku"]: Decimal(str(item["sale_price"]))
            for item in self.catalog["products"]
        }
        self.assertEqual(
            prices,
            {
                "SUN-SEEKER-100": Decimal("545"),
                "SUN-SAND-100": Decimal("595"),
                "SUN-BUNDLE-100": Decimal("999"),
            },
        )
        self.assertEqual(self.catalog["retrieved_at"], "2026-07-30")

    def test_capitalization_is_exactly_one_million(self):
        capitalization = self.assumptions["capitalization"]
        shares = sum(item["shares"] for item in capitalization["contributors"])
        amount = sum(
            Decimal(str(item["amount"]))
            for item in capitalization["contributors"]
        )
        self.assertEqual(shares, 1_000_000)
        self.assertEqual(amount, Decimal("1000000"))
        self.assertEqual(capitalization["contributors"][-1]["shares"], 1)

    def test_requested_people_and_recurring_costs(self):
        salaries = {
            item["job_title"]: item["monthly_gross"]
            for item in self.assumptions["people"]["employees"]
        }
        self.assertEqual(salaries["In-house Marketing Manager"], 40000.0)
        self.assertEqual(salaries["In-house Logistics Coordinator"], 30000.0)
        contractor = self.assumptions["people"]["contractors"][0]
        self.assertEqual(contractor["monthly_gross"], 6000.0)
        self.assertEqual(contractor["atc"], "WI010")
        self.assertEqual(contractor["expanded_withholding_rate"], 0.05)
        self.assertEqual(
            sum(
                Decimal(str(item["monthly_compensation_withholding"]))
                for item in self.assumptions["people"]["employees"]
            ),
            Decimal("4583.45"),
        )
        expenses = {
            item["label"]: item["amount"]
            for item in self.assumptions["monthly_expenses"]
        }
        self.assertEqual(expenses["Shopify subscription"], 1200.0)
        self.assertEqual(
            expenses["Gmail / Google Workspace subscription"], 1100.0
        )
        self.assertEqual(expenses["Digital advertising spend"], 10000.0)
        self.assertEqual(expenses["Office and goods storage rent"], 20000.0)
        self.assertEqual(expenses["Electricity utility bill"], 4000.0)

    def test_requested_one_time_expenses(self):
        expenses = {
            item["label"]: item for item in self.assumptions["one_time_expenses"]
        }
        self.assertEqual(
            expenses["Local company incorporation package"]["amount"], 45000.0
        )
        self.assertEqual(expenses["Printer ink"]["amount"], 2400.0)
        pens = expenses["Five pens at PHP 25 each"]
        self.assertEqual(pens["quantity"], 5)
        self.assertEqual(pens["amount"], pens["quantity"] * pens["unit_price"])

    def test_assets_use_five_year_straight_line(self):
        assets = self.assumptions["fixed_assets"]
        self.assertEqual(len(assets), 3)
        self.assertEqual(
            [item["name"].startswith("MacBook M2") for item in assets].count(True),
            2,
        )
        self.assertTrue(any(item["name"] == "Office printer" for item in assets))
        for asset in assets:
            self.assertEqual(asset["useful_life_months"], 60)
            self.assertEqual(asset["residual_value"], 0.0)

    def test_unit_cogs_breakdowns(self):
        totals = {
            item["sku"]: sum(
                Decimal(str(amount)) for amount in item["unit_cogs"].values()
            )
            for item in self.catalog["products"]
        }
        self.assertEqual(
            totals,
            {
                "SUN-SEEKER-100": Decimal("190"),
                "SUN-SAND-100": Decimal("225"),
                "SUN-BUNDLE-100": Decimal("430"),
            },
        )

    def test_orders_cover_every_month_and_reconcile(self):
        expected = self.assumptions["sales"]["orders_per_month"]
        by_month = Counter(row["order_date"][:7] for row in self.orders)
        self.assertEqual(len(by_month), 12)
        self.assertEqual(set(by_month.values()), {expected})
        products = {
            item["sku"]: item for item in self.catalog["products"]
        }
        charged_shipping = 0
        for row in self.orders:
            subtotal = sum(
                Decimal(row[sku]) * Decimal(str(item["sale_price"]))
                for sku, item in products.items()
            )
            self.assertEqual(subtotal, Decimal(row["product_subtotal"]))
            expected_charge = (
                Decimal("0")
                if subtotal
                >= Decimal(
                    str(self.assumptions["sales"]["free_shipping_threshold"])
                )
                else Decimal(
                    str(
                        self.assumptions["sales"][
                            "customer_shipping_charge_below_threshold"
                        ]
                    )
                )
            )
            self.assertEqual(expected_charge, Decimal(row["shipping_charge"]))
            expected_lalamove = Decimal(
                str(
                    self.assumptions["sales"]["lalamove_zone_rates"][row["city"]]
                )
            )
            self.assertEqual(expected_lalamove, Decimal(row["lalamove_cost"]))
            charged_shipping += bool(expected_charge)
        self.assertGreater(charged_shipping, 0)
        self.assertLess(charged_shipping, len(self.orders))

    def test_expected_statements_balance(self):
        module_path = ROOT / "scripts" / "validate_dataset.py"
        spec = importlib.util.spec_from_file_location("validate_dataset", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        summary = module.calculate(self.assumptions, self.catalog, self.orders)
        self.assertEqual(
            summary["closing_cash"] + summary["fixed_asset_nbv"],
            summary["closing_equity"],
        )
        self.assertGreater(summary["closing_cash"], 0)
        self.assertEqual(
            summary["compensation_withholding_monthly"], Decimal("4583.45")
        )
        self.assertEqual(
            summary["expanded_withholding_monthly"], Decimal("300")
        )

    def test_1601c_input_reconciles_to_assumptions(self):
        form = json.loads(
            (
                ROOT
                / "tax_forms"
                / "2025-12-1601C"
                / "input.json"
            ).read_text(encoding="utf-8")
        )
        fields = form["fields"]
        gross = sum(
            Decimal(str(item["monthly_gross"]))
            for item in self.assumptions["people"]["employees"]
        )
        withholding = sum(
            Decimal(str(item["monthly_compensation_withholding"]))
            for item in self.assumptions["people"]["employees"]
        )
        self.assertEqual(Decimal(fields["txtTax14"]), gross)
        for key in ("txtTax25", "txtTax27", "txtTax31", "txtTax36"):
            self.assertEqual(Decimal(fields[key]), withholding)
        self.assertEqual(
            form["profile"]["tin"], self.assumptions["company"]["vat"]
        )
        self.assertLessEqual(len(fields["txtNumber37"]), 17)

    def test_cli_generated_1601c_pdf_is_tracked_and_checksummed(self):
        pdf_dir = ROOT / "output" / "pdf"
        pdf = pdf_dir / "the-sun-people-form-1601c-2025-12.pdf"
        data = pdf.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", data[-1024:])
        self.assertGreater(len(data), 900_000)

        checksum_line = (pdf_dir / "SHA256SUMS").read_text(
            encoding="utf-8"
        ).strip()
        expected_hash, filename = checksum_line.split()
        self.assertEqual(filename, pdf.name)
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)


if __name__ == "__main__":
    unittest.main()
