#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cli=${EBIRFORMS_CLI:-}
template=${EBIRFORMS_1601C_PDF_TEMPLATE:-}
expected_template_sha=c8faaa71015337a73b4ceb96bfb265c539589ab5e10eb27899bb81f87f417397

if [ -z "$cli" ] || [ ! -x "$cli" ]; then
  echo "Set EBIRFORMS_CLI to a built ebirforms-cli executable." >&2
  exit 2
fi

if [ -z "$template" ] || [ ! -f "$template" ]; then
  echo "Set EBIRFORMS_1601C_PDF_TEMPLATE to the official January 2018 Form 1601-C PDF." >&2
  exit 2
fi

template_sha=$(shasum -a 256 "$template" | awk '{print $1}')
if [ "$template_sha" != "$expected_template_sha" ]; then
  echo "Unexpected Form 1601-C PDF template SHA-256: $template_sha" >&2
  echo "Expected: $expected_template_sha" >&2
  exit 2
fi

form_dir="$repo_root/tax_forms/2025-12-1601C"
pdf_dir="$repo_root/output/pdf"
input="$form_dir/input.json"
pdf="$pdf_dir/the-sun-people-form-1601c-2025-12.pdf"

mkdir -p "$pdf_dir"

"$cli" render \
  --form 1601C \
  --input "$input" \
  --out "$form_dir/plaintext.xml"

"$cli" package \
  --form 1601C \
  --input "$input" \
  --out "$form_dir/upload.xml" \
  --manifest "$form_dir/manifest.json"

"$cli" render-pdf \
  --form 1601C \
  --xml "$form_dir/plaintext.xml" \
  --template "$template" \
  --out "$pdf"

(
  cd "$form_dir"
  shasum -a 256 \
    input.json \
    plaintext.xml \
    upload.xml \
    manifest.json \
    CLI_PROVENANCE.txt > SHA256SUMS
)

(
  cd "$pdf_dir"
  shasum -a 256 the-sun-people-form-1601c-2025-12.pdf > SHA256SUMS
)

echo "Prepared synthetic Form 1601-C XML artifacts in $form_dir"
echo "Prepared synthetic Form 1601-C PDF in $pdf"
