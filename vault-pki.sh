#!/usr/bin/env bash
set -euo pipefail

PKI_DIR="${1:-.pki}"

declare -A VAR_NAMES=(
  ["crazy.lab-key.pem"]="sat_cert_private_key_content"
  ["crazy.lab-wildcard.pem"]="sat_cert_public_key_content"
  ["crazy.lab-ca.pem"]="sat_cert_ca_content"
  ["crazy.lab-chain.pem"]="sat_cert_ca_bundle_content"
)

for file in "$PKI_DIR"/*.pem; do
  basename=$(basename "$file")
  varname="${VAR_NAMES[$basename]:-}"

  if [[ -z "$varname" ]]; then
    echo "# Skipping unknown file: $basename" >&2
    continue
  fi

  echo "${varname}: !vault |"
  ansible-vault encrypt_string --stdin-name _dummy < "$file" 2>/dev/null \
    | sed -n '/\$ANSIBLE_VAULT/,$ p' \
    | sed 's/^  /          /'
  echo ""
done
