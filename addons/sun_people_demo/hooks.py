"""Install a deterministic, synthetic Philippines operating ledger."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from odoo import Command
from odoo.exceptions import UserError


DATA_DIR = Path(__file__).resolve().parent / "data"
SEED_KEY = "sun_people_demo.seeded_version"
SEED_VERSION = "2025.1"
ZERO = Decimal("0")


def _json(name: str) -> dict:
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _orders() -> list[dict]:
    with (DATA_DIR / "synthetic_orders.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _account(env, company, code: str):
    account = (
        env["account.account"]
        .with_company(company)
        .search(
            [
                ("code", "=", code),
                ("company_ids", "in", company.ids),
            ],
            limit=1,
        )
    )
    if not account:
        raise UserError(f"Required Philippine chart account {code} was not found.")
    return account


def _journal(env, company, journal_type: str):
    journal = env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", journal_type)],
        limit=1,
    )
    if not journal:
        raise UserError(f"Required {journal_type!r} journal was not found.")
    return journal


def _partner(env, country, name: str, **values):
    existing = env["res.partner"].search(
        [("name", "=", name), ("company_id", "=", False)],
        limit=1,
    )
    if existing:
        return existing
    return env["res.partner"].create(
        {
            "name": name,
            "country_id": country.id,
            **values,
        }
    )


def _post_entry(env, company, journal, entry_date, ref: str, lines: list[dict]):
    debit = sum(Decimal(str(line.get("debit", 0))) for line in lines)
    credit = sum(Decimal(str(line.get("credit", 0))) for line in lines)
    if debit.quantize(Decimal("0.01")) != credit.quantize(Decimal("0.01")):
        raise UserError(f"Unbalanced fixture entry {ref}: debit {debit}, credit {credit}")

    move = (
        env["account.move"]
        .with_company(company)
        .create(
            {
                "move_type": "entry",
                "company_id": company.id,
                "journal_id": journal.id,
                "date": entry_date,
                "ref": ref,
                "line_ids": [
                    Command.create(
                        {
                            "name": line["name"],
                            "account_id": line["account"].id,
                            "partner_id": line.get("partner").id
                            if line.get("partner")
                            else False,
                            "debit": float(line.get("debit", 0)),
                            "credit": float(line.get("credit", 0)),
                        }
                    )
                    for line in lines
                ],
            }
        )
    )
    move.action_post()
    return move


def _configure_company(env, assumptions):
    company = env.company
    country = env.ref("base.ph")
    currency = env.ref("base.PHP")
    company_data = assumptions["company"]

    existing_moves = env["account.move"].search_count(
        [("company_id", "=", company.id), ("state", "=", "posted")]
    )
    if company.chart_template and company.chart_template != "ph" and existing_moves:
        raise UserError(
            "The Sun People fixture must be installed on a fresh database because "
            "switching fiscal localizations after entries are posted is unsafe."
        )

    company.write(
        {
            "name": company_data["name"],
            "country_id": country.id,
            "currency_id": currency.id,
        }
    )
    env["account.chart.template"].try_loading(
        "ph", company, install_demo=False, force_create=True
    )
    company = env["res.company"].browse(company.id)
    company.partner_id.write(
        {
            "name": company_data["name"],
            "street": company_data["street"],
            "street2": company_data["street2"],
            "city": company_data["city"],
            "zip": company_data["zip"],
            "country_id": country.id,
            "vat": company_data["vat"],
            "l10n_ph_rdo": company_data["rdo"],
            "email": company_data["email"],
            "phone": company_data["phone"],
        }
    )
    return company, country


def _create_people(env, assumptions, country):
    partners = {}
    for contributor in assumptions["capitalization"]["contributors"]:
        partners[contributor["name"]] = _partner(
            env,
            country,
            contributor["name"],
            comment=(
                f"Synthetic shareholder: {contributor['shares']:,} shares at "
                f"PHP {assumptions['capitalization']['par_value']:.2f} par."
            ),
        )

    for employee in assumptions["people"]["employees"]:
        partner = _partner(
            env,
            country,
            employee["name"],
            email=f"{employee['name'].split()[0].lower()}@sunpeople.demo.invalid",
        )
        partners[employee["name"]] = partner
        env["hr.employee"].create(
            {
                "name": employee["name"],
                "job_title": employee["job_title"],
                "work_email": partner.email,
            }
        )

    for contractor in assumptions["people"]["contractors"]:
        partners[contractor["name"]] = _partner(
            env,
            country,
            contractor["name"],
            is_company=False,
            supplier_rank=1,
            vat=contractor["tin"],
            first_name=contractor["first_name"],
            middle_name=contractor["middle_name"],
            last_name=contractor["last_name"],
            street=contractor["street"],
            city=contractor["city"],
            zip=contractor["zip"],
            comment=contractor["qualification"],
        )

    all_vendors = {
        expense["vendor"] for expense in assumptions["monthly_expenses"]
    }
    all_vendors.update(
        expense["vendor"] for expense in assumptions["one_time_expenses"]
    )
    all_vendors.update(asset["vendor"] for asset in assumptions["fixed_assets"])
    all_vendors.update(
        {
            "Bureau of Internal Revenue (Synthetic Clearing Partner)",
            "Lalamove (Demo Vendor)",
            "Demo Contract Manufacturer",
        }
    )
    for vendor in sorted(all_vendors):
        partners[vendor] = _partner(
            env, country, vendor, is_company=True, supplier_rank=1
        )

    return partners


def _create_products(env, company, catalog):
    income = _account(env, company, "430400")
    products = {}
    for item in catalog["products"]:
        total_cost = sum(Decimal(str(value)) for value in item["unit_cogs"].values())
        template = (
            env["product.template"]
            .with_company(company)
            .create(
                {
                    "name": item["name"],
                    "default_code": item["sku"],
                    "type": "consu",
                    "sale_ok": True,
                    "purchase_ok": False,
                    "invoice_policy": "order",
                    "list_price": item["sale_price"],
                    "standard_price": float(total_cost),
                    "taxes_id": [Command.clear()],
                    "supplier_taxes_id": [Command.clear()],
                    "property_account_income_id": income.id,
                    "description_sale": (
                        "Public catalog fact; all order activity and cost assumptions "
                        "in this database are synthetic."
                    ),
                }
            )
        )
        products[item["sku"]] = template.product_variant_id

    shipping = (
        env["product.template"]
        .with_company(company)
        .create(
            {
                "name": "Shipping fee",
                "default_code": "SHIPPING-DEMO",
                "type": "service",
                "sale_ok": True,
                "purchase_ok": False,
                "invoice_policy": "order",
                "list_price": 150.0,
                "taxes_id": [Command.clear()],
                "supplier_taxes_id": [Command.clear()],
                "property_account_income_id": income.id,
            }
        )
    )
    products["SHIPPING-DEMO"] = shipping.product_variant_id
    return products


def _post_capital(env, company, assumptions, partners, journal, bank):
    capital = _account(env, company, "300000")
    contributors = assumptions["capitalization"]["contributors"]
    total = sum(Decimal(str(item["amount"])) for item in contributors)
    lines = [
        {
            "name": "Paid-in capitalization",
            "account": bank,
            "debit": total,
        }
    ]
    lines.extend(
        {
            "name": (
                f"{item['name']} - {item['shares']:,} shares at "
                f"PHP {assumptions['capitalization']['par_value']:.2f}"
            ),
            "account": capital,
            "partner": partners[item["name"]],
            "credit": Decimal(str(item["amount"])),
        }
        for item in contributors
    )
    _post_entry(
        env,
        company,
        journal,
        date(assumptions["demo_year"], 1, 1),
        "TSP-DEMO-CAPITAL",
        lines,
    )


def _post_assets(env, company, assumptions, partners, journal, bank):
    by_date = defaultdict(list)
    for asset in assumptions["fixed_assets"]:
        by_date[date.fromisoformat(asset["date"])].append(asset)

    for asset_date, assets in sorted(by_date.items()):
        lines = []
        total = ZERO
        for asset in assets:
            cost = Decimal(str(asset["cost"]))
            total += cost
            lines.append(
                {
                    "name": (
                        f"{asset['asset_id']} {asset['name']} - "
                        f"{asset['useful_life_months']}-month straight line"
                    ),
                    "account": _account(
                        env, company, asset["asset_account_code"]
                    ),
                    "partner": partners[asset["vendor"]],
                    "debit": cost,
                }
            )
        lines.append(
            {
                "name": "Cash purchase of demo fixed assets",
                "account": bank,
                "credit": total,
            }
        )
        _post_entry(
            env,
            company,
            journal,
            asset_date,
            "TSP-DEMO-ASSET-PURCHASES",
            lines,
        )

    for month in range(1, 13):
        month_end = date(
            assumptions["demo_year"],
            month,
            monthrange(assumptions["demo_year"], month)[1],
        )
        lines = []
        for asset in assumptions["fixed_assets"]:
            monthly = (
                Decimal(str(asset["cost"]))
                - Decimal(str(asset["residual_value"]))
            ) / Decimal(str(asset["useful_life_months"]))
            lines.extend(
                [
                    {
                        "name": f"{asset['asset_id']} {asset['name']}",
                        "account": _account(
                            env,
                            company,
                            asset["depreciation_expense_account_code"],
                        ),
                        "debit": monthly,
                    },
                    {
                        "name": f"{asset['asset_id']} accumulated depreciation",
                        "account": _account(
                            env,
                            company,
                            asset["accumulated_depreciation_account_code"],
                        ),
                        "credit": monthly,
                    },
                ]
            )
        _post_entry(
            env,
            company,
            journal,
            month_end,
            f"TSP-DEMO-DEPRECIATION-{month:02d}",
            lines,
        )


def _post_one_time_expenses(
    env, company, assumptions, partners, journal, bank
):
    for expense in assumptions["one_time_expenses"]:
        amount = Decimal(str(expense["amount"]))
        _post_entry(
            env,
            company,
            journal,
            date.fromisoformat(expense["date"]),
            f"TSP-DEMO-ONE-TIME-{expense['label'].upper()[:20]}",
            [
                {
                    "name": expense["label"],
                    "account": _account(env, company, expense["account_code"]),
                    "partner": partners[expense["vendor"]],
                    "debit": amount,
                },
                {
                    "name": f"Paid to {expense['vendor']}",
                    "account": bank,
                    "credit": amount,
                },
            ],
        )


def _post_monthly_operating_costs(
    env, company, assumptions, partners, journal, bank
):
    salary_account = _account(env, company, "623000")
    compensation_withholding = _account(env, company, "200306")
    bir_partner = partners[
        "Bureau of Internal Revenue (Synthetic Clearing Partner)"
    ]
    for month in range(1, 13):
        month_end = date(
            assumptions["demo_year"],
            month,
            monthrange(assumptions["demo_year"], month)[1],
        )
        lines = []
        total = ZERO
        tax_withheld = ZERO
        for employee in assumptions["people"]["employees"]:
            amount = Decimal(str(employee["monthly_gross"]))
            total += amount
            employee_tax = Decimal(
                str(employee["monthly_compensation_withholding"])
            )
            tax_withheld += employee_tax
            lines.append(
                {
                    "name": (
                        f"{employee['job_title']} - gross salary "
                        f"{month_end:%Y-%m}"
                    ),
                    "account": salary_account,
                    "partner": partners[employee["name"]],
                    "debit": amount,
                }
            )
            lines.append(
                {
                    "name": (
                        f"{employee['job_title']} compensation tax withheld "
                        f"{month_end:%Y-%m}"
                    ),
                    "account": compensation_withholding,
                    "partner": bir_partner,
                    "credit": employee_tax,
                }
            )
        for expense in assumptions["monthly_expenses"]:
            amount = Decimal(str(expense["amount"]))
            total += amount
            lines.append(
                {
                    "name": f"{expense['label']} {month_end:%Y-%m}",
                    "account": _account(env, company, expense["account_code"]),
                    "partner": partners[expense["vendor"]],
                    "debit": amount,
                }
            )
        total_net_cash = total - tax_withheld
        lines.append(
            {
                "name": (
                    f"Net payroll and monthly operating cash disbursements "
                    f"{month_end:%Y-%m}"
                ),
                "account": bank,
                "credit": total_net_cash,
            }
        )
        _post_entry(
            env,
            company,
            journal,
            month_end,
            f"TSP-DEMO-OPEX-{month:02d}",
            lines,
        )
        _post_entry(
            env,
            company,
            journal,
            month_end,
            f"TSP-DEMO-1601C-REMITTANCE-{month:02d}",
            [
                {
                    "name": (
                        f"Form 1601-C compensation withholding remitted "
                        f"{month_end:%Y-%m}"
                    ),
                    "account": compensation_withholding,
                    "partner": bir_partner,
                    "debit": tax_withheld,
                },
                {
                    "name": (
                        f"Form 1601-C cash remittance {month_end:%Y-%m}"
                    ),
                    "account": bank,
                    "credit": tax_withheld,
                },
            ],
        )


def _create_contractor_bills(
    env,
    company,
    assumptions,
    partners,
    general_journal,
    bank_journal,
    bank,
):
    contractor = assumptions["people"]["contractors"][0]
    contractor_partner = partners[contractor["name"]]
    professional_fees = _account(env, company, "626001")
    ewt_payable = _account(env, company, "200301")
    bir_partner = partners[
        "Bureau of Internal Revenue (Synthetic Clearing Partner)"
    ]
    existing_professional_tax = env["account.tax"].search(
        [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "purchase"),
            ("l10n_ph_atc", "=", contractor["atc"]),
            ("amount", "=", -100 * contractor["expanded_withholding_rate"]),
        ],
        limit=1,
    )
    if existing_professional_tax:
        professional_tax = existing_professional_tax
    else:
        prototype = env["account.tax"].search(
            [
                ("company_id", "=", company.id),
                ("type_tax_use", "=", "purchase"),
                ("l10n_ph_atc", "=", "WI011"),
            ],
            limit=1,
        )
        professional_tax = env["account.tax"].create(
            {
                "name": "5% WI010 - Individual Professional Fees",
                "description": (
                    "Professional fees - individual payee not over PHP 3M"
                ),
                "invoice_label": "5% WI010",
                "amount": -100 * contractor["expanded_withholding_rate"],
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "tax_scope": "service",
                "tax_exigibility": "on_invoice",
                "company_id": company.id,
                "tax_group_id": prototype.tax_group_id.id
                if prototype
                else False,
                "l10n_ph_atc": contractor["atc"],
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": ewt_payable.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": ewt_payable.id,
                        }
                    ),
                ],
            }
        )

    for month in range(1, 13):
        month_end = date(
            assumptions["demo_year"],
            month,
            monthrange(assumptions["demo_year"], month)[1],
        )
        gross = Decimal(str(contractor["monthly_gross"]))
        withheld = gross * Decimal(
            str(contractor["expanded_withholding_rate"])
        )
        bill = (
            env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": "in_invoice",
                    "company_id": company.id,
                    "partner_id": contractor_partner.id,
                    "invoice_date": month_end,
                    "date": month_end,
                    "ref": f"TSP-ACCT-{assumptions['demo_year']}-{month:02d}",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": (
                                    f"{contractor['service']} "
                                    f"{month_end:%Y-%m}"
                                ),
                                "quantity": 1,
                                "price_unit": float(gross),
                                "account_id": professional_fees.id,
                                "tax_ids": [Command.set(professional_tax.ids)],
                            }
                        )
                    ],
                }
            )
        )
        bill.action_post()
        (
            env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=bill.ids,
                dont_redirect_to_payments=True,
            )
            .create(
                {
                    "payment_date": month_end,
                    "journal_id": bank_journal.id,
                    "amount": bill.amount_residual,
                }
            )
            ._create_payments()
        )
        _post_entry(
            env,
            company,
            general_journal,
            month_end,
            f"TSP-DEMO-EWT-REMITTANCE-{month:02d}",
            [
                {
                    "name": (
                        f"Expanded withholding remitted for "
                        f"{contractor['name']} {month_end:%Y-%m}"
                    ),
                    "account": ewt_payable,
                    "partner": bir_partner,
                    "debit": withheld,
                },
                {
                    "name": (
                        f"Expanded withholding cash remittance "
                        f"{month_end:%Y-%m}"
                    ),
                    "account": bank,
                    "credit": withheld,
                },
            ],
        )


def _create_sales(
    env, company, country, assumptions, catalog, products, bank_journal
):
    rows = sorted(_orders(), key=lambda row: (row["order_date"], row["order_id"]))
    customer_cities = {}
    for row in rows:
        customer_cities.setdefault(row["customer"], row["city"])
    customers = {
        name: _partner(
            env,
            country,
            name,
            city=city,
            customer_rank=1,
            comment="Fictional customer generated for the FY2025 demo.",
        )
        for name, city in customer_cities.items()
    }

    catalog_by_sku = {item["sku"]: item for item in catalog["products"]}
    for row in rows:
        order_lines = []
        for sku, item in catalog_by_sku.items():
            quantity = int(row[sku])
            if not quantity:
                continue
            order_lines.append(
                Command.create(
                    {
                        "product_id": products[sku].id,
                        "product_uom_qty": quantity,
                        "price_unit": item["sale_price"],
                        "tax_ids": [Command.clear()],
                    }
                )
            )
        shipping_charge = Decimal(row["shipping_charge"])
        if shipping_charge:
            order_lines.append(
                Command.create(
                    {
                        "product_id": products["SHIPPING-DEMO"].id,
                        "product_uom_qty": 1,
                        "price_unit": float(shipping_charge),
                        "tax_ids": [Command.clear()],
                    }
                )
            )

        order_day = date.fromisoformat(row["order_date"])
        order = (
            env["sale.order"]
            .with_company(company)
            .create(
                {
                    "company_id": company.id,
                    "partner_id": customers[row["customer"]].id,
                    "date_order": datetime.combine(
                        order_day, datetime.min.time()
                    ),
                    "client_order_ref": row["order_id"],
                    "note": (
                        f"Synthetic delivery to {row['city']}; Lalamove model cost "
                        f"PHP {row['lalamove_cost']}."
                    ),
                    "order_line": order_lines,
                }
            )
        )
        order.action_confirm()
        order.date_order = datetime.combine(order_day, datetime.min.time())
        invoice = order._create_invoices()
        invoice.write(
            {
                "invoice_date": order_day,
                "date": order_day,
                "ref": row["order_id"],
            }
        )
        invoice.action_post()
        (
            env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=invoice.ids,
                dont_redirect_to_payments=True,
            )
            .create(
                {
                    "payment_date": order_day,
                    "journal_id": bank_journal.id,
                    "amount": invoice.amount_residual,
                }
            )
            ._create_payments()
        )


def _post_order_driven_costs(
    env, company, assumptions, catalog, partners, journal, bank
):
    orders_by_month = defaultdict(list)
    for row in _orders():
        orders_by_month[date.fromisoformat(row["order_date"]).month].append(row)
    catalog_by_sku = {item["sku"]: item for item in catalog["products"]}
    component_accounts = {
        "formulation_and_filling": "511700",
        "primary_packaging": "511100",
        "labels_and_cartons": "511800",
        "inbound_freight": "511600",
    }
    lalamove = partners["Lalamove (Demo Vendor)"]
    manufacturer = partners["Demo Contract Manufacturer"]

    for month, rows in sorted(orders_by_month.items()):
        month_end = date(
            assumptions["demo_year"],
            month,
            monthrange(assumptions["demo_year"], month)[1],
        )
        components = defaultdict(lambda: ZERO)
        for row in rows:
            for sku, item in catalog_by_sku.items():
                quantity = Decimal(row[sku])
                for component, unit_cost in item["unit_cogs"].items():
                    components[component] += quantity * Decimal(str(unit_cost))

        cogs_total = sum(components.values(), ZERO)
        cogs_lines = [
            {
                "name": f"Monthly COGS - {component.replace('_', ' ')}",
                "account": _account(env, company, component_accounts[component]),
                "partner": manufacturer,
                "debit": amount,
            }
            for component, amount in sorted(components.items())
        ]
        cogs_lines.append(
            {
                "name": f"Paid monthly production COGS {month_end:%Y-%m}",
                "account": bank,
                "credit": cogs_total,
            }
        )
        _post_entry(
            env,
            company,
            journal,
            month_end,
            f"TSP-DEMO-COGS-{month:02d}",
            cogs_lines,
        )

        shipping_total = sum(
            (Decimal(row["lalamove_cost"]) for row in rows), ZERO
        )
        shipping_lines = [
            {
                "name": (
                    f"{row['order_id']} Lalamove delivery - {row['city']}"
                ),
                "account": _account(env, company, "627000"),
                "partner": lalamove,
                "debit": Decimal(row["lalamove_cost"]),
            }
            for row in rows
        ]
        shipping_lines.append(
            {
                "name": f"Paid Lalamove deliveries {month_end:%Y-%m}",
                "account": bank,
                "credit": shipping_total,
            }
        )
        _post_entry(
            env,
            company,
            journal,
            month_end,
            f"TSP-DEMO-LALAMOVE-{month:02d}",
            shipping_lines,
        )


def post_init_hook(env):
    parameters = env["ir.config_parameter"].sudo()
    if parameters.get_param(SEED_KEY) == SEED_VERSION:
        return

    assumptions = _json("assumptions.json")
    catalog = _json("catalog_snapshot.json")
    company, country = _configure_company(env, assumptions)
    env = env(
        context={
            **env.context,
            "allowed_company_ids": [company.id],
            "force_company": company.id,
            "tracking_disable": True,
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
        }
    )
    company = env["res.company"].browse(company.id)

    bank_journal = _journal(env, company, "bank")
    general_journal = _journal(env, company, "general")
    bank_account = bank_journal.default_account_id
    if not bank_account:
        raise UserError("The Philippine bank journal has no default liquidity account.")

    partners = _create_people(env, assumptions, country)
    products = _create_products(env, company, catalog)
    _post_capital(
        env,
        company,
        assumptions,
        partners,
        general_journal,
        bank_account,
    )
    _post_assets(
        env,
        company,
        assumptions,
        partners,
        general_journal,
        bank_account,
    )
    _post_one_time_expenses(
        env,
        company,
        assumptions,
        partners,
        general_journal,
        bank_account,
    )
    _post_monthly_operating_costs(
        env,
        company,
        assumptions,
        partners,
        general_journal,
        bank_account,
    )
    _create_contractor_bills(
        env,
        company,
        assumptions,
        partners,
        general_journal,
        bank_journal,
        bank_account,
    )
    _create_sales(
        env,
        company,
        country,
        assumptions,
        catalog,
        products,
        bank_journal,
    )
    _post_order_driven_costs(
        env,
        company,
        assumptions,
        catalog,
        partners,
        general_journal,
        bank_account,
    )
    parameters.set_param(SEED_KEY, SEED_VERSION)
