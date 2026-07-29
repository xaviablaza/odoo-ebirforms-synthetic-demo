# Expected FY2025 ledger summary

This report is generated from the committed fixture by
`python3 scripts/validate_dataset.py --write-report`. It describes the balances
expected after Odoo installs `sun_people_demo`.

## Activity

- Confirmed, invoiced, and paid synthetic orders: 216
- Product revenue: ₱1,403,366.00
- Customer shipping revenue: ₱1,050.00
- Total revenue: ₱1,404,416.00
- Lalamove delivery expense: ₱32,400.00

| SKU | Units sold | Public unit price |
| --- | ---: | ---: |
| SUN-SEEKER-100 | 660 | ₱545.00 |
| SUN-SAND-100 | 656 | ₱595.00 |
| SUN-BUNDLE-100 | 654 | ₱999.00 |

## COGS

| Component | FY2025 amount |
| --- | ---: |
| Formulation And Filling | ₱335,832.00 |
| Inbound Freight | ₱31,488.00 |
| Labels And Cartons | ₱59,662.00 |
| Primary Packaging | ₱127,238.00 |
| **Total COGS** | **₱554,220.00** |

COGS is paid monthly and is derived directly from the SKU quantities in
`synthetic_orders.csv`. There is no opening or closing inventory in this
cash-basis demo.

## Operating costs

- Monthly employee gross payroll: ₱70,000.00
- Monthly accounting contractor: ₱6,000.00
- Monthly subscriptions, ads, rent, and electricity: ₱36,300.00
- FY2025 recurring operating expense: ₱1,347,600.00
- One-time incorporation and office supplies: ₱47,525.00

## Withholding forms

- December 2025 Form 1601-C compensation withholding: ₱4,583.45
- FY2025 compensation withholding/remittances: ₱55,001.40
- Monthly accounting-contractor expanded withholding: ₱300.00
- Q4 2025 Form 2307 income payments: ₱18,000.00
- Q4 2025 Form 2307 tax withheld (WI010 at 5%): ₱900.00
- FY2025 contractor expanded withholding/remittances: ₱3,600.00

The Form 1601-C input is rendered by the external Rust CLI. Odoo creates the
contractor vendor bills and its Philippine localization exports the selected
Q4 bills through **Download BIR 2307 XLS**.

## Fixed assets

| Asset ID | Asset | Cost | Life (months) | Monthly depreciation |
| --- | --- | ---: | ---: | ---: |
| FA-2025-001 | MacBook M2 - Marketing | ₱72,000.00 | 60 | ₱1,200.00 |
| FA-2025-002 | MacBook M2 - Logistics | ₱72,000.00 | 60 | ₱1,200.00 |
| FA-2025-003 | Office printer | ₱18,000.00 | 60 | ₱300.00 |

- Capitalized cost: ₱162,000.00
- FY2025 depreciation: ₱32,400.00
- Closing fixed-asset net book value: ₱129,600.00

## Reconciled expected statements

| Item | Amount |
| --- | ---: |
| Paid-in capital | ₱1,000,000.00 |
| FY2025 net income / (loss) | ₱-609,729.00 |
| Closing equity | ₱390,271.00 |
| Closing cash | ₱260,671.00 |
| Closing fixed assets, net | ₱129,600.00 |
| **Closing assets** | **₱390,271.00** |

The expected balance sheet balances to the cent. Taxes, statutory payroll
deductions, employer contributions, receivables, payables, and inventory are
intentionally outside this educational fixture.
