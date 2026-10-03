#!/usr/bin/env bash
# Build the PyPI `frob` wheel for this host: frob via maturin (bindings=bin), grimble
# via cargo, copied into the wheel's scripts. Usage: build-wheel.sh [--out DIR]
# Never publishes. Honors CARGO_TARGET_DIR (default: <repo>/target) and WHEEL_COMPAT
# (maturin --compatibility value, default manylinux_2_28 on Linux; "off" lets the host decide).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
out="$root/target/wheels"
if [[ "${1:-}" == "--out" ]]; then out="$(realpath -m "${2:?--out needs a directory}")"; fi
target="${CARGO_TARGET_DIR:-$root/target}"
venv="$target/maturin-venv"

echo "build-wheel: maturin environment in $venv" >&2
uv venv -q --clear "$venv"
uv pip install -q --python "$venv/bin/python" "maturin>=1.9,<2"
"$venv/bin/maturin" --version >&2

echo "build-wheel: building grimble (release)" >&2
cargo build --release --locked -p grimble --manifest-path "$root/Cargo.toml" --target-dir "$target"
exe=""; [[ "${OS:-}" == "Windows_NT" ]] && exe=".exe"
mkdir -p "$here/data/scripts"
install -m 0755 "$target/release/grimble$exe" "$here/data/scripts/grimble$exe"

echo "build-wheel: building the wheel into $out" >&2
mkdir -p "$out"
compat=()
case "$(uname -s)" in Linux) c="${WHEEL_COMPAT:-manylinux_2_28}"; [[ "$c" == off ]] || compat=(--compatibility "$c");; esac
(cd "$here" && "$venv/bin/maturin" build --release --locked --out "$out" "${compat[@]}" --target-dir "$target")
ls -1 "$out"/frob-*.whl
