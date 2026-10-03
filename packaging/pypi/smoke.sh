#!/usr/bin/env bash
# Smoke a built frob wheel: check its metadata (name frob, platform tag, optional version),
# install it into a clean venv with uv and run the shipped executables.
# Usage: smoke.sh WHEEL [EXPECTED_VERSION]   (the repository loop is packaging/smoke/fixture-loop.sh, ~NWXQPMM)
set -euo pipefail

wheel="$(realpath "${1:?usage: smoke.sh WHEEL [EXPECTED_VERSION]}")"
want="${2:-}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# venv layout: Scripts/ on Windows, bin/ elsewhere. The wheel is read with the venv's python
# (zipfile) because Git Bash on Windows has no unzip.
bin="$work/venv/bin"; [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* || "${OS:-}" == "Windows_NT" ]] && bin="$work/venv/Scripts"
uv venv -q "$work/venv"
dist_info() { "$bin/python" -c 'import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
name = next(n for n in z.namelist() if n.endswith(".dist-info/" + sys.argv[2]))
sys.stdout.write(z.read(name).decode())' "$wheel" "$1"; }
meta="$(dist_info METADATA)"
tag="$(dist_info WHEEL | sed -n 's/^Tag: //p' | tr -d '\r')"
echo "smoke: wheel $(basename "$wheel") tag=$tag" >&2
tr -d '\r' <<<"$meta" | grep -qx 'Name: frob' || { echo "smoke: metadata name is not frob" >&2; exit 1; }
if [[ "$(uname -s)" == Linux && "${WHEEL_COMPAT:-}" != off && "$tag" != *manylinux_2_28* ]]; then
    echo "smoke: linux tag is not manylinux_2_28 ($tag)" >&2; exit 1
fi

uv pip install -q --python "$bin/python" "$wheel"
got="$("$bin/frob" --version | tr -d '\r')"; echo "$got"
"$bin/grimble" --version
if [[ -n "$want" && "$got" != "frob $want" ]]; then
    echo "smoke: expected 'frob $want', got '$got'" >&2; exit 1
fi
# The shared fixture-repository loop (init through land) with the installed binaries.
"$(dirname "$0")/../smoke/fixture-loop.sh" "$bin" "$want"
echo "smoke: ok"
