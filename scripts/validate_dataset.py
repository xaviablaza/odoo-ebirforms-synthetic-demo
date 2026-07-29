#!/usr/bin/env python3
"""Validate the fixture and reconcile its expected FY2025 statements."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "addons" / "sun_people_demo" / "data"
REPORT = ROOT / "reports" / "expected_ledger_summary.md"
ZERO = Decimal("0")


def money(value: Decimal) -> str:
    return f"₱{value:,.2f}"


def load() -> tuple[dict, dict, list[dict]]:
    assumptions = json.loads(
        (DATA_DIR / "assumptions.json").read_text(encoding="utf-8")
    )
    catalog = json.loads(
        (DATA_DIR / "catalog_snapshot.json").read_text(encoding="utf-8")
    )
    with (DATA_DIR / "synthetic_orders.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        orders = list(csv.DictReader(handle))
    return assumptions, catalog, orders


def calculate(assumptions: dict, catalog: dict, orders: list[dict]) -> dict:
    products = {item["sku"]: item for item in catalog["products"]}
    monthly_order_counts = Counter(row["order_date"][:7] for row in orders)
    units = Counter()
    product_revenue = ZERO
    shipping_revenue = ZERO
    lalamove = ZERO
    cogs_components = defaultdict(lambda: ZERO)

    for row in orders:
        subtotal = ZERO
        for sku, product in products.items():
            quantity = int(row[sku])
            units[sku] += quantity
            subtotal += Decimal(quantity) * Decimal(str(product["sale_price"]))
            for component, unit_cost in product["unit_cogs"].items():
                cogs_components[component] += Decimal(quantity) * Decimal(
                    str(unit_cost)
                )
        if subtotal != Decimal(row["product_subtotal"]):
            raise ValueError(f"{row['order_id']} product subtotal is inconsistent")
        expected_shipping = (
            ZERO
            if subtotal
            >= Decimal(str(assumptions["sales"]["free_shipping_threshold"]))
            else Decimal(
                str(
                    assumptions["sales"][
                        "customer_shipping_charge_below_threshold"
                    ]
                )
            )
        )
        if expected_shipping != Decimal(row["shipping_charge"]):
            raise ValueError(f"{row['order_id']} shipping policy is inconsistent")
        zone_rate = Decimal(
            str(assumptions["sales"]["lalamove_zone_rates"][row["city"]])
        )
        if zone_rate != Decimal(row["lalamove_cost"]):
            raise ValueError(f"{row['order_id']} Lalamove rate is inconsistent")
        product_revenue += subtotal
        shipping_revenue += Decimal(row["shipping_charge"])
        lalamove += zone_rate

    expected_month_count = assumptions["sales"]["orders_per_month"]
    if len(monthly_order_counts) != 12 or set(monthly_order_counts.values()) != {
        expected_month_count
    }:
        raise ValueError("The fixture must contain the configured order count each month")

    salary_monthly = sum(
        Decimal(str(item["monthly_gross"]))
        for item in assumptions["people"]["employees"]
    )
    contractors_monthly = sum(
        Decimal(str(item["monthly_gross"]))
        for item in assumptions["people"]["contractors"]
    )
    compensation_withholding_monthly = sum(
        Decimal(str(item["monthly_compensation_withholding"]))
        for item in assumptions["people"]["employees"]
    )
    expanded_withholding_monthly = sum(
        Decimal(str(item["monthly_gross"]))
        * Decimal(str(item["expanded_withholding_rate"]))
        for item in assumptions["people"]["contractors"]
    )
    other_monthly = sum(
        Decimal(str(item["amount"])) for item in assumptions["monthly_expenses"]
    )
    recurring_expenses = Decimal(12) * (
        salary_monthly + contractors_monthly + other_monthly
    )
    one_time_expenses = sum(
        (Decimal(str(item["amount"])) for item in assumptions["one_time_expenses"]),
        ZERO,
    )
    fixed_asset_cost = sum(
        (Decimal(str(item["cost"])) for item in assumptions["fixed_assets"]), ZERO
    )
    monthly_depreciation = sum(
        (
            (
                Decimal(str(item["cost"]))
                - Decimal(str(item["residual_value"]))
            )
            / Decimal(str(item["useful_life_months"]))
            for item in assumptions["fixed_assets"]
        ),
        ZERO,
    )
    depreciation = Decimal(12) * monthly_depreciation
    capital = sum(
        (
            Decimal(str(item["amount"]))
            for item in assumptions["capitalization"]["contributors"]
        ),
        ZERO,
    )
    cogs = sum(cogs_components.values(), ZERO)
    revenue = product_revenue + shipping_revenue
    cash_expenses = recurring_expenses + one_time_expenses + cogs + lalamove
    closing_cash = capital + revenue - cash_expenses - fixed_asset_cost
    net_income = revenue - cash_expenses - depreciation
    fixed_asset_nbv = fixed_asset_cost - depreciation
    closing_equity = capital + net_income

    if closing_cash + fixed_asset_nbv != closing_equity:
        raise ValueError("Expected balance sheet does not balance")

    return {
        "orders": len(orders),
        "monthly_order_counts": monthly_order_counts,
        "units": units,
        "product_revenue": product_revenue,
        "shipping_revenue": shipping_revenue,
        "revenue": revenue,
        "cogs_components": cogs_components,
        "cogs": cogs,
        "lalamove": lalamove,
        "salary_monthly": salary_monthly,
        "contractors_monthly": contractors_monthly,
        "compensation_withholding_monthly": compensation_withholding_monthly,
        "compensation_withholding_annual": (
            Decimal(12) * compensation_withholding_monthly
        ),
        "expanded_withholding_monthly": expanded_withholding_monthly,
        "expanded_withholding_annual": (
            Decimal(12) * expanded_withholding_monthly
        ),
        "other_monthly": other_monthly,
        "recurring_expenses": recurring_expenses,
        "one_time_expenses": one_time_expenses,
        "fixed_asset_cost": fixed_asset_cost,
        "monthly_depreciation": monthly_depreciation,
        "depreciation": depreciation,
        "fixed_asset_nbv": fixed_asset_nbv,
        "capital": capital,
        "closing_cash": closing_cash,
        "net_income": net_income,
        "closing_equity": closing_equity,
    }


def render(summary: dict, assumptions: dict, catalog: dict) -> str:
    unit_rows = "\n".join(
        f"| {product['sku']} | {summary['units'][product['sku']]:,} | "
        f"{money(Decimal(str(product['sale_price'])))} |"
        for product in catalog["products"]
    )
    cogs_rows = "\n".join(
        f"| {component.replace('_', ' ').title()} | {money(amount)} |"
        for component, amount in sorted(summary["cogs_components"].items())
    )
    assets = "\n".join(
        f"| {asset['asset_id']} | {asset['name']} | "
        f"{money(Decimal(str(asset['cost'])))} | "
        f"{asset['useful_life_months']} | "
        f"{money(Decimal(str(asset['cost'])) / Decimal(str(asset['useful_life_months'])))} |"
        for asset in assumptions["fixed_assets"]
    )
    return f"""# Expected FY2025 ledger summary

This report is generated from the committed fixture by
`python3 scripts/validate_dataset.py --write-report`. It describes the balances
expected after Odoo installs `sun_people_demo`.

## Activity

- Confirmed, invoiced, and paid synthetic orders: {summary['orders']:,}
- Product revenue: {money(summary['product_revenue'])}
- Customer shipping revenue: {money(summary['shipping_revenue'])}
- Total revenue: {money(summary['revenue'])}
- Lalamove delivery expense: {money(summary['lalamove'])}

| SKU | Units sold | Public unit price |
| --- | ---: | ---: |
{unit_rows}

## COGS

| Component | FY2025 amount |
| --- | ---: |
{cogs_rows}
| **Total COGS** | **{money(summary['cogs'])}** |

COGS is paid monthly and is derived directly from the SKU quantities in
`synthetic_orders.csv`. There is no opening or closing inventory in this
cash-basis demo.

## Operating costs

- Monthly employee gross payroll: {money(summary['salary_monthly'])}
- Monthly accounting contractor: {money(summary['contractors_monthly'])}
- Monthly subscriptions, ads, rent, and electricity: {money(summary['other_monthly'])}
- FY2025 recurring operating expense: {money(summary['recurring_expenses'])}
- One-time incorporation and office supplies: {money(summary['one_time_expenses'])}

## Withholding forms

- December 2025 Form 1601-C compensation withholding: {money(summary['compensation_withholding_monthly'])}
- FY2025 compensation withholding/remittances: {money(summary['compensation_withholding_annual'])}
- Monthly accounting-contractor expanded withholding: {money(summary['expanded_withholding_monthly'])}
- Q4 2025 Form 2307 income payments: {money(summary['contractors_monthly'] * Decimal(3))}
- Q4 2025 Form 2307 tax withheld (WI010 at 5%): {money(summary['expanded_withholding_monthly'] * Decimal(3))}
- FY2025 contractor expanded withholding/remittances: {money(summary['expanded_withholding_annual'])}

The Form 1601-C input is rendered by the external Rust CLI. Odoo creates the
contractor vendor bills and its Philippine localization exports the selected
Q4 bills through **Download BIR 2307 XLS**.

## Fixed assets

| Asset ID | Asset | Cost | Life (months) | Monthly depreciation |
| --- | --- | ---: | ---: | ---: |
{assets}

- Capitalized cost: {money(summary['fixed_asset_cost'])}
- FY2025 depreciation: {money(summary['depreciation'])}
- Closing fixed-asset net book value: {money(summary['fixed_asset_nbv'])}

## Reconciled expected statements

| Item | Amount |
| --- | ---: |
| Paid-in capital | {money(summary['capital'])} |
| FY2025 net income / (loss) | {money(summary['net_income'])} |
| Closing equity | {money(summary['closing_equity'])} |
| Closing cash | {money(summary['closing_cash'])} |
| Closing fixed assets, net | {money(summary['fixed_asset_nbv'])} |
| **Closing assets** | **{money(summary['closing_cash'] + summary['fixed_asset_nbv'])}** |

The expected balance sheet balances to the cent. Taxes, statutory payroll
deductions, employer contributions, receivables, payables, and inventory are
intentionally outside this educational fixture.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="replace the committed expected summary",
    )
    args = parser.parse_args()
    assumptions, catalog, orders = load()
    summary = calculate(assumptions, catalog, orders)
    form_1601c = json.loads(
        (ROOT / "tax_forms" / "2025-12-1601C" / "input.json").read_text(
            encoding="utf-8"
        )
    )
    fields_1601c = form_1601c["fields"]
    expected_1601c = summary["compensation_withholding_monthly"]
    if Decimal(fields_1601c["txtTax14"]) != summary["salary_monthly"]:
        raise SystemExit("Form 1601-C gross compensation does not match the ledger")
    for field in ("txtTax25", "txtTax27", "txtTax31", "txtTax36"):
        if Decimal(fields_1601c[field]) != expected_1601c:
            raise SystemExit(
                f"Form 1601-C {field} does not match compensation withholding"
            )
    if form_1601c["profile"]["tin"] != assumptions["company"]["vat"]:
        raise SystemExit("Form 1601-C TIN does not match the synthetic company")
    report = render(summary, assumptions, catalog)

    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report, encoding="utf-8")
        print(f"Wrote {REPORT.relative_to(ROOT)}")
    elif not REPORT.exists() or REPORT.read_text(encoding="utf-8") != report:
        raise SystemExit(
            "reports/expected_ledger_summary.md is stale; "
            "run `python3 scripts/validate_dataset.py --write-report`."
        )

    print(
        "Validated "
        f"{summary['orders']} orders, {money(summary['revenue'])} revenue, "
        f"{money(summary['cogs'])} COGS, and a balanced "
        f"{money(summary['closing_cash'] + summary['fixed_asset_nbv'])} "
        "closing balance sheet."
    )


if __name__ == "__main__":
    main()
