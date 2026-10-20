#!/usr/bin/env bash
# Make the frob ledger refs resolvable as LOCAL branches in a CI checkout (ticket 01M5CY4615SPGHB682NX2S3S24).
# Pull requests check out a detached merge commit, so neither the [tickets] code ref nor,
# in orphan mode, the ticket branch exists locally; frob fails with E-LEDGER-REF-MISSING otherwise.
set -euo pipefail

toml="${1:-frob.toml}"

# Value of `key = "..."` inside the [tickets] table, or the default.
tickets_value() {
  awk -v key="$1" -v def="$2" '
    /^\[/ { in_t = ($0 == "[tickets]") }
    in_t && $1 == key && $2 == "=" { gsub(/"/, "", $3); print $3; found = 1; exit }
    END { if (!found) print def }
  ' "$toml"
}

# Create local refs/heads/NAME from origin when missing; return 1 when origin lacks it.
ensure_local() {
  local name="$1"
  if git rev-parse --verify -q "refs/heads/${name}" >/dev/null; then
    return 0
  fi
  git fetch --no-tags origin "+refs/heads/${name}:refs/remotes/origin/${name}" || return 1
  git update-ref "refs/heads/${name}" "refs/remotes/origin/${name}"
  echo "ensure-ledger-refs: created local ${name} from origin/${name}"
}

ref="$(tickets_value ref refs/heads/experimental)"
mode="$(tickets_value ref_mode inline)"
branch="$(tickets_value branch frob-tickets)"

ensure_local "${ref#refs/heads/}"

if [ "${mode}" = "orphan" ]; then
  # Origin must have the ticket branch in orphan mode; a missing one is a real error.
  ensure_local "${branch}" || { echo "ensure-ledger-refs: origin has no ${branch}" >&2; exit 1; }
fi
