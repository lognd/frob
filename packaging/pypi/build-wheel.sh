#!/usr/bin/env bash
# Build the PyPI wheel of every product (products.toml: frob, grimble) for this host, one wheel
# each, each carrying only its own binary (D87). render.py writes each product's maturin project
# under <target>/pypi/<product>; maturin (bindings=bin) builds it. Never publishes.
# Usage: build-wheel.sh [--out DIR] [--target TRIPLE] [--product NAME]...
# --target is forwarded to maturin (cross builds, e.g. the macOS x86_64 wheels on an arm64
# runner); --product limits the build (default: every product). maturin comes from
# maturin-requirements.txt (exact version, sha256 verified by --require-hashes). Honors
# CARGO_TARGET_DIR (default: <repo>/target) and WHEEL_COMPAT (maturin --compatibility, default
# manylinux_2_28 on Linux; "off" = host decides).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
out="$root/target/wheels"
triple=""
only=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out) out="$(realpath -m "${2:?--out needs a directory}")"; shift 2;;
        --target) triple="${2:?--target needs a rust target triple}"; shift 2;;
        --product) only+=("${2:?--product needs a product name}"); shift 2;;
        *) echo "usage: build-wheel.sh [--out DIR] [--target TRIPLE] [--product NAME]..." >&2; exit 2;;
    esac
done
target="${CARGO_TARGET_DIR:-$root/target}"
venv="$target/maturin-venv"
# venv layout: Scripts/ on Windows, bin/ elsewhere.
vbin="$venv/bin"; [[ "${OS:-}" == "Windows_NT" ]] && vbin="$venv/Scripts"

echo "build-wheel: maturin environment in $venv" >&2
uv venv -q --clear --python ">=3.11" "$venv"
uv pip install -q --require-hashes --no-deps --python "$vbin/python" -r "$here/maturin-requirements.txt"
"$vbin/maturin" --version >&2

products=()
while IFS= read -r p; do products+=("${p%$'\r'}"); done < <("$vbin/python" "$here/render.py" list)
if [[ ${#only[@]} -gt 0 ]]; then products=("${only[@]}"); fi

tflag=()
if [[ -n "$triple" ]]; then tflag=(--target "$triple"); fi
compat=()
case "$(uname -s)" in Linux) c="${WHEEL_COMPAT:-manylinux_2_28}"; [[ "$c" == off ]] || compat=(--compatibility "$c");; esac
mkdir -p "$out"
for product in "${products[@]}"; do
    proj="$target/pypi/$product"
    echo "build-wheel: $product: rendering $proj" >&2
    rm -rf "$proj"
    "$vbin/python" "$here/render.py" render "$product" "$proj"
    echo "build-wheel: $product: building the wheel into $out" >&2
    (cd "$proj" && "$vbin/maturin" build --release --locked --out "$out" ${compat[@]+"${compat[@]}"} ${tflag[@]+"${tflag[@]}"} --target-dir "$target")
    ls -1 "$out/$product"-*.whl
done
