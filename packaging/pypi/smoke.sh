#!/usr/bin/env bash
# Smoke a built frob wheel: check its metadata (name frob, platform tag, optional version),
# install it into a clean venv with uv and run the shipped executables.
# Usage: smoke.sh WHEEL [EXPECTED_VERSION]   (the artifact smoke ticket NWXQPMM builds on this)
set -euo pipefail

wheel="$(realpath "${1:?usage: smoke.sh WHEEL [EXPECTED_VERSION]}")"
want="${2:-}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

meta="$(unzip -p "$wheel" '*.dist-info/METADATA')"
tag="$(unzip -p "$wheel" '*.dist-info/WHEEL' | sed -n 's/^Tag: //p')"
echo "smoke: wheel $(basename "$wheel") tag=$tag" >&2
grep -qx 'Name: frob' <<<"$meta" || { echo "smoke: metadata name is not frob" >&2; exit 1; }
if [[ "$(uname -s)" == Linux && "$tag" != *manylinux_2_28* ]]; then
    echo "smoke: linux tag is not manylinux_2_28 ($tag)" >&2; exit 1
fi

uv venv -q "$work/venv"
uv pip install -q --python "$work/venv/bin/python" "$wheel"
bin="$work/venv/bin"
got="$("$bin/frob" --version)"; echo "$got"
"$bin/grimble" --version
if [[ -n "$want" && "$got" != "frob $want" ]]; then
    echo "smoke: expected 'frob $want', got '$got'" >&2; exit 1
fi
git init -q "$work/repo"
(cd "$work/repo" && "$bin/frob" doctor >/dev/null)
echo "smoke: ok"
