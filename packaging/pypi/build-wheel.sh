#!/usr/bin/env bash
# Build the PyPI `frob` wheel for this host: frob via maturin (bindings=bin), grimble
# via cargo, copied into the wheel's scripts. Usage: build-wheel.sh [--out DIR] [--target TRIPLE]
# Never publishes. --target is forwarded to cargo and maturin (cross builds, e.g. the macOS
# x86_64 wheel on an arm64 runner). Honors CARGO_TARGET_DIR (default: <repo>/target),
# MATURIN_VERSION (pip requirement, default ">=1.9,<2"; the release workflow pins "==X.Y.Z")
# and WHEEL_COMPAT (maturin --compatibility, default manylinux_2_28 on Linux; "off" = host decides).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
out="$root/target/wheels"
triple=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out) out="$(realpath -m "${2:?--out needs a directory}")"; shift 2;;
        --target) triple="${2:?--target needs a rust target triple}"; shift 2;;
        *) echo "usage: build-wheel.sh [--out DIR] [--target TRIPLE]" >&2; exit 2;;
    esac
done
target="${CARGO_TARGET_DIR:-$root/target}"
venv="$target/maturin-venv"
# venv layout: Scripts/ on Windows, bin/ elsewhere.
vbin="$venv/bin"; [[ "${OS:-}" == "Windows_NT" ]] && vbin="$venv/Scripts"

echo "build-wheel: maturin environment in $venv" >&2
uv venv -q --clear "$venv"
uv pip install -q --python "$vbin/python" "maturin${MATURIN_VERSION:->=1.9,<2}"
"$vbin/maturin" --version >&2

echo "build-wheel: building grimble (release)" >&2
tflag=(); rel="$target/release"
if [[ -n "$triple" ]]; then tflag=(--target "$triple"); rel="$target/$triple/release"; fi
cargo build --release --locked -p grimble --manifest-path "$root/Cargo.toml" --target-dir "$target" ${tflag[@]+"${tflag[@]}"}
exe=""; [[ "${OS:-}" == "Windows_NT" ]] && exe=".exe"
mkdir -p "$here/data/scripts"
install -m 0755 "$rel/grimble$exe" "$here/data/scripts/grimble$exe"

echo "build-wheel: building the wheel into $out" >&2
mkdir -p "$out"
compat=()
case "$(uname -s)" in Linux) c="${WHEEL_COMPAT:-manylinux_2_28}"; [[ "$c" == off ]] || compat=(--compatibility "$c");; esac
(cd "$here" && "$vbin/maturin" build --release --locked --out "$out" ${compat[@]+"${compat[@]}"} ${tflag[@]+"${tflag[@]}"} --target-dir "$target")
ls -1 "$out"/frob-*.whl
