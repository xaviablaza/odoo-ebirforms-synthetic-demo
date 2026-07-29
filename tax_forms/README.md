# Prepared synthetic tax-form artifacts

These files are educational dry-run artifacts only. Every TIN, address,
identity, transaction, and payment reference is synthetic. Nothing in this
directory is authorized for filing.

## December 2025 Form 1601-C

`2025-12-1601C/input.json` is derived from the Odoo assumptions and December
ledger entries:

- Gross taxable compensation: ₱70,000.00
- Marketing manager withholding: ₱3,208.40
- Logistics coordinator withholding: ₱1,375.05
- Total compensation tax withheld/remitted: ₱4,583.45

The rates use the BIR monthly withholding table effective January 1, 2023
onward. The demo intentionally assumes no employee statutory-contribution
deductions, so it is not a payroll calculator or filing recommendation.

The XML, dry-run package, and sample PDF are generated with
[`xaviablaza/ebirforms-rebuilt-rs-oss`](https://github.com/xaviablaza/ebirforms-rebuilt-rs-oss)
at the merged PDF-export commit recorded in `CLI_PROVENANCE.txt`. The CLI
overlays the XML values on the official BIR January 2018 blank form supplied at
runtime; the blank template is not committed to this repository.

```bash
EBIRFORMS_CLI=/path/to/ebirforms-cli \
EBIRFORMS_1601C_PDF_TEMPLATE=/path/to/official-1601C.pdf \
./scripts/render_1601c.sh
```

The expected blank template is the
[official BIR Form 1601-C PDF](https://bir-cdn.bir.gov.ph/local/pdf/1601C%20final%20Jan%202018%20with%20DPA.pdf)
with SHA-256
`c8faaa71015337a73b4ceb96bfb265c539589ab5e10eb27899bb81f87f417397`.
The generated two-page sample is
`output/pdf/the-sun-people-form-1601c-2025-12.pdf`; visually review it before
any real-world use. No submission command is part of the script.

## Q4 2025 Form 2307

Form 2307 is generated natively in Odoo, not by the Rust CLI. The seed creates
monthly vendor bills for the synthetic individual accounting contractor with:

- Q4 professional fees: ₱6,000 in October, November, and December
- Q4 income payments: ₱18,000
- ATC: WI010
- Expanded withholding rate: 5%
- Q4 tax withheld: ₱900

In Odoo, open **Accounting → Vendors → Bills**, select the three Q4 bills with
references `TSP-ACCT-2025-10` through `TSP-ACCT-2025-12`, then choose
**Actions → Download BIR 2307 XLS → Generate**.

The 5% treatment assumes an individual, non-VAT professional with annual gross
income not over ₱3 million who supplied the required declaration and
Certificate of Registration. That is a synthetic scenario assumption, not a
fact about any person.
