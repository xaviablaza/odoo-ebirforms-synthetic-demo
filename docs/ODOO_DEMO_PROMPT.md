# Prompt: demonstrate the synthetic Odoo accounting and withholding flow

Use this prompt with an agent that can control the browser and terminal:

---

You are demonstrating the local “The Sun People (Synthetic Demo)” Odoo 19
Community database. Use the browser to click through Odoo and the terminal only
for read-only verification. Narrate each screen concisely and capture
screenshots where useful.

Safety rules:

- This is synthetic educational data. Never submit, email, or upload a tax
  form, and never enable any live-filing mode.
- Do not edit, delete, cancel, reset, or reconcile records during the demo.
- Do not expose secrets or environment variables.
- If the database is unavailable, report the exact blocker; do not rebuild or
  reset volumes without permission.

Open `http://localhost:8069` and sign in with `admin` / `admin`.

1. Confirm the company and localization.
   - Open Settings and show the active company name, Philippine country, and
     PHP currency.
   - Open Accounting → Configuration → Settings and show the Philippines
     fiscal localization.

2. Show capitalization.
   - Open Accounting → Accounting → Journal Entries.
   - Search Reference for `TSP-DEMO-CAPITAL`.
   - Open the entry and show the ₱1,000,000 bank debit, three ₱333,333 founder
     credits, and the corporate secretary’s ₱1 credit.

3. Show one representative sale from order to cash.
   - Open Sales → Orders → Orders.
   - Search Customer Reference for `TSP-2025-0001`.
   - Show its public catalog lines, quantities, product subtotal, synthetic
     delivery city, and Lalamove model cost in the note.
   - Open the linked customer invoice and show that it is posted and paid.
   - Open its journal items to show receivable, sales revenue, and payment.

4. Show December operating expenses and compensation withholding.
   - Return to Accounting → Accounting → Journal Entries.
   - Open `TSP-DEMO-OPEX-12`; show gross salary expense of ₱40,000 and ₱30,000,
     the individual compensation-withholding credits of ₱3,208.40 and
     ₱1,375.05, and the net cash disbursement.
   - Open `TSP-DEMO-1601C-REMITTANCE-12`; show the ₱4,583.45 debit clearing the
     withholding liability and matching bank credit.

5. Show subscriptions, advertising, storage rent, and electricity.
   - In `TSP-DEMO-OPEX-12`, point out Shopify ₱1,200, Google Workspace ₱1,100,
     advertising ₱10,000, office/goods-storage rent ₱20,000, and electricity
     ₱4,000.

6. Show order-driven direct costs and delivery.
   - Open `TSP-DEMO-COGS-12`; show formulation/filling, primary packaging,
     labels/cartons, and inbound-freight lines.
   - Open `TSP-DEMO-LALAMOVE-12`; show that each line references a specific
     order and Metro Manila delivery zone.

7. Show fixed assets and depreciation.
   - Open `TSP-DEMO-ASSET-PURCHASES`; show two ₱72,000 MacBook M2 assets and
     the ₱18,000 printer.
   - Open `TSP-DEMO-DEPRECIATION-12`; show ₱1,200 monthly depreciation for each
     laptop and ₱300 for the printer, with matching accumulated depreciation.
   - Show the printer ink and five pens in their January one-time expense
     entries.

8. Show the outsourced accountant and native Odoo Form 2307 path.
   - Open Accounting → Vendors → Bills.
   - Filter Vendor to `Alex Ledger (Synthetic)`.
   - Open bill reference `TSP-ACCT-2025-12`.
   - Show the ₱6,000 professional fee, custom `5% WI010 - Individual
     Professional Fees` tax, ₱300 tax withheld, ₱5,700 net payment, posted
     status, and paid status.
   - Return to the bill list and select exactly
     `TSP-ACCT-2025-10`, `TSP-ACCT-2025-11`, and
     `TSP-ACCT-2025-12`.
   - Choose Actions → Download BIR 2307 XLS.
   - In the wizard, verify that only those three bills are selected.
   - Click Generate to download the synthetic `Form_2307.xls`.
   - State that Q4 income payments total ₱18,000 and tax withheld totals ₱900.
     Do not upload the XLS anywhere.

9. Verify the prepared Form 1601-C artifacts in the terminal.
   - From the repository root, run
     `python3 scripts/validate_dataset.py`.
   - Show `tax_forms/2025-12-1601C/manifest.json` and
     `tax_forms/2025-12-1601C/SHA256SUMS`.
   - Explain that the Rust CLI rendered and packaged a dry-run December 2025
     1601-C with ₱70,000 gross compensation and ₱4,583.45 withholding.
   - Do not run any `submit`, `queue`, or live network command.

10. Finish with a concise reconciliation:
    - 216 paid synthetic orders.
    - ₱1,404,416 total revenue.
    - ₱554,220 order-derived COGS.
    - ₱4,583.45 December compensation withholding.
    - ₱900 Q4 contractor withholding on Form 2307.
    - ₱390,271 closing assets and equity.

---
