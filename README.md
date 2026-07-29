# The Sun People — synthetic Odoo Philippines demo

A one-command Odoo 19 Community environment configured for a fictionalized
Philippine operating company, **The Sun People (Synthetic Demo)**. Installing
the included add-on creates a complete FY2025 sample ledger with products,
customers, employees, vendors, sales orders, paid customer invoices, operating
expenses, paid-in capital, fixed assets, and manual straight-line depreciation.

> This project is an independent educational demo. It is not affiliated with,
> endorsed by, or a representation of The Sun People, Korp.ph, Lalamove,
> Shopify, Google, Apple, or any other named party. Except for the cited public
> shop names/prices and Korp.ph advertised starting fee, every identity,
> transaction, cost, address, and tax identifier is synthetic.

## Start it

Requirements: Docker Desktop (or Docker Engine with Compose v2) and about 2 GB
of free memory.

```bash
cp .env.example .env
docker compose up -d
docker compose logs -f odoo
```

Open [http://localhost:8069](http://localhost:8069) when the Odoo service is
healthy. The development-only login is:

- Email: `admin`
- Password: `admin`

The first boot pulls Odoo 19 and PostgreSQL 15, creates the
`sun_people_demo` database, installs the Philippine localization and the custom
fixture, then starts Odoo. Later boots reuse the two named volumes.

Useful commands:

```bash
make check       # validate source fixtures and expected accounting statements
make logs        # follow Odoo
make stop        # stop containers and preserve data
make reset       # delete demo volumes; the next start rebuilds everything
```

`make reset` is intentionally destructive to this demo's Docker volumes.

## What is seeded

The add-on installs the stock Odoo 19 Community Philippine chart
(`l10n_ph`), PHP currency, a fictional Makati address and TIN, and these FY2025
events:

- ₱1,000,000 paid-in capital: three founders contribute ₱333,333 / 333,333
  shares each and a corporate secretary contributes ₱1 / one share.
- 216 synthetic Sales Orders across all 12 months. Every order is confirmed,
  invoiced, and paid. Catalog lines use the public shop prices captured on
  2026-07-30.
- Customer shipping follows the public “free shipping for orders ₱1,500 and
  up” banner. Lalamove expense is independently calculated at a synthetic
  ₱120–₱180 per order based on six Metro Manila delivery zones.
- Monthly COGS is derived from actual units in those orders and paid to a
  synthetic contract manufacturer. Four line items are booked: formulation and
  filling, primary packaging, labels/cartons, and inbound freight.
- Gross monthly pay of ₱40,000 for a marketing manager and ₱30,000 for a
  logistics coordinator, with compensation withholding and remittance entries.
- A ₱6,000 monthly accounting-contractor vendor bill carrying a synthetic 5%
  WI010 expanded-withholding tax, paid net of withholding and available to
  Odoo’s native BIR 2307 XLS exporter.
- Monthly Shopify ₱1,200, Gmail/Google Workspace ₱1,100, ad spend ₱10,000,
  office and goods-storage rent ₱20,000, and electricity ₱4,000.
- A one-time ₱45,000 Korp.ph local-incorporation package expense.
- Two ₱72,000 MacBook M2 laptops and one ₱18,000 printer capitalized and
  depreciated straight-line over 60 months with zero residual value.
- One ₱2,400 printer-ink purchase and five pens at ₱25 each expensed
  immediately.

The checked-in [expected ledger summary](reports/expected_ledger_summary.md)
reconciles the generated dataset independently of Odoo.

## Source facts and modeling boundaries

Public facts captured in
[`catalog_snapshot.json`](addons/sun_people_demo/data/catalog_snapshot.json):

| Product | Captured price |
| --- | ---: |
| Sun Seeker SPF 50+ 100mL | ₱545 |
| Sun+Sand Shield SPF 50+ 100mL | ₱595 |
| Sun Seeker + Sun+Sand bundle | ₱999 (from ₱1,140) |

Sources:

- [The Sun People shop](https://www.thesunpeople.com/collections/shop),
  retrieved 2026-07-30.
- [Korp.ph solutions](https://www.korp.ph/solutions), retrieved 2026-07-30;
  “Incorporation for Filipinos” advertised as starting at ₱45,000.
- [Odoo 19 Philippine localization
  documentation](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/philippines.html).

The product COGS breakdown, asset prices, rent, electricity, Lalamove rates,
customers, order quantities, and all people are explicit synthetic assumptions.
They are not claims about the real business.

The demo deliberately does **not** model VAT, income tax, employee statutory
contribution deductions, employer SSS/PhilHealth/Pag-IBIG contributions, or
inventory balances. It does model simplified compensation withholding and
expanded withholding for the synthetic accounting contractor. COGS is booked
monthly on a direct cash basis. Have a Philippine accountant review every
policy before adapting this to real books.

## Prepared withholding-form demo

The [synthetic tax-form artifacts](tax_forms/README.md) reconcile to the seeded
ledger:

- December 2025 Form 1601-C: ₱70,000 gross compensation and ₱4,583.45
  compensation tax withheld. The input is rendered, dry-run packaged, and
  overlaid on the official blank BIR form with the upstream Rust CLI PDF-export
  feature. The generated sample is
  [`output/pdf/the-sun-people-form-1601c-2025-12.pdf`](output/pdf/the-sun-people-form-1601c-2025-12.pdf).
  Nothing is submitted.
- Q4 2025 Form 2307: three ₱6,000 contractor bills, ₱18,000 total income
  payments, and ₱900 WI010 tax withheld. Generate it in Odoo by selecting the
  October–December bills and choosing **Actions → Download BIR 2307 XLS**.

The 5% professional-fee assumption applies only to the documented synthetic
individual/non-VAT scenario. The [Odoo walkthrough
prompt](docs/ODOO_DEMO_PROMPT.md) provides a complete click-by-click demo.

## Change the scenario

Most editable inputs are in
[`assumptions.json`](addons/sun_people_demo/data/assumptions.json). Public
catalog facts and synthetic unit-cost assumptions are kept separately in
[`catalog_snapshot.json`](addons/sun_people_demo/data/catalog_snapshot.json).

After changing order-generation inputs or catalog prices:

```bash
make generate-orders
python3 scripts/validate_dataset.py --write-report
make check
make reset
make start
```

`scripts/refresh_catalog.py` can refresh the Shopify JSON endpoint, but it
refuses new/renamed products until a human supplies reviewed COGS assumptions:

```bash
make refresh-catalog
make generate-orders
python3 scripts/validate_dataset.py --write-report
make check
```

## Repository layout

```text
addons/sun_people_demo/      Odoo add-on and source fixtures
config/odoo.conf             development Odoo configuration
scripts/generate_orders.py   deterministic order generator
scripts/validate_dataset.py  independent accounting reconciliation
scripts/refresh_catalog.py   optional public-catalog refresh
tests/                       fixture policy and balancing tests
tax_forms/                   reconciled dry-run 1601-C inputs and artifacts
output/pdf/                  CLI-generated sample Form 1601-C PDF
docs/                        Odoo demonstration prompt
compose.yaml                 Odoo 19 + PostgreSQL 15
```

The custom code is MIT-licensed. Odoo and the container images retain their
own licenses.
