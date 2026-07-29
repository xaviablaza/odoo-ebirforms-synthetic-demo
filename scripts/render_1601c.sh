#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cli=${EBIRFORMS_CLI:-}

if [ -z "$cli" ] || [ ! -x "$cli" ]; then
  echo "Set EBIRFORMS_CLI to a built ebirforms-cli executable." >&2
  exit 2
fi

form_dir="$repo_root/tax_forms/2025-12-1601C"
input="$form_dir/input.json"

"$cli" render \
  --form 1601C \
  --input "$input" \
  --out "$form_dir/plaintext.xml"

"$cli" package \
  --form 1601C \
  --input "$input" \
  --out "$form_dir/upload.xml" \
  --manifest "$form_dir/manifest.json"

(
  cd "$form_dir"
  shasum -a 256 \
    input.json \
    plaintext.xml \
    upload.xml \
    manifest.json \
    CLI_PROVENANCE.txt > SHA256SUMS
)

echo "Prepared synthetic Form 1601-C artifacts in $form_dir"
