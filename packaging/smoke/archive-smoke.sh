#!/bin/sh
# Smoke one product's standalone cargo-dist archive (.tar.xz or .zip): unpack it into a
# clean directory and run the product's binary. The archives are named after the package
# (frob-cli-<target>, grimble-<target>, crunk-<target>; docs/design/releases.md 6), so callers pass each
# product archive explicitly. For `frob` this is the shared fixture-repository loop
# (fixture-loop.sh); for `grimble` and `crunk` it is `<product> --version` (plus EXPECTED_VERSION when given) and
# `<product> doctor`.
# Usage: archive-smoke.sh PRODUCT ARCHIVE [EXPECTED_VERSION]   (PRODUCT: frob, grimble or crunk;
# POSIX sh; Git Bash on Windows)
set -eu

product="${1:?usage: archive-smoke.sh PRODUCT ARCHIVE [EXPECTED_VERSION]}"
archive="${2:?usage: archive-smoke.sh PRODUCT ARCHIVE [EXPECTED_VERSION]}"
want="${3:-}"
case "$product" in
    frob | grimble | crunk) ;;
    *) echo "smoke-archive: unknown product: $product (expected frob, grimble or crunk)" >&2; exit 1 ;;
esac
[ -f "$archive" ] || { echo "smoke-archive: missing archive: $archive" >&2; exit 1; }
here="$(cd "$(dirname "$0")" && pwd)"
archive="$(cd "$(dirname "$archive")" && pwd)/$(basename "$archive")"
work="$(mktemp -d)"
trap 'cd /; rm -rf "$work"' EXIT

echo "smoke-archive: $product: $(basename "$archive")" >&2
mkdir "$work/unpacked"
case "$archive" in
    *.tar.xz) tar -xJf "$archive" -C "$work/unpacked" ;;
    # Git Bash has no unzip; the runners' python reads zips everywhere.
    *.zip) "$(command -v python3 || command -v python)" -m zipfile -e "$archive" "$work/unpacked" ;;
    *) echo "smoke-archive: unknown archive type: $archive" >&2; exit 1 ;;
esac
exe="$(find "$work/unpacked" \( -name "$product" -o -name "$product.exe" \) -type f | head -n 1)"
[ -n "$exe" ] || { echo "smoke-archive: no $product executable in $archive" >&2; exit 1; }
chmod +x "$exe" 2>/dev/null || true
# One product per archive (D87): no other product's binary may ride along.
for other in frob grimble crunk fake-sibling; do
    [ "$other" = "$product" ] && continue
    if find "$work/unpacked" \( -name "$other" -o -name "$other.exe" \) -type f | grep -q .; then
        echo "smoke-archive: $archive also carries $other" >&2; exit 1
    fi
done
case "$product" in
    frob) "$here/fixture-loop.sh" "$(dirname "$exe")" "$want" ;;
    grimble | crunk)
        got="$("$exe" --version | tr -d '\r')"
        echo "smoke-archive: $got" >&2
        case "$got" in "$product ${want:-}"*) ;; *) echo "smoke-archive: expected '$product ${want:-}', got '$got'" >&2; exit 1 ;; esac
        # doctor runs in an empty directory (no config); only a crash or a usage error fails.
        mkdir "$work/doctor"
        (cd "$work/doctor" && "$exe" doctor >/dev/null) || { echo "smoke-archive: $product doctor failed" >&2; exit 1; }
        ;;
esac
echo "smoke-archive: ok"
