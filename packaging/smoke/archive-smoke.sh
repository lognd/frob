#!/bin/sh
# Smoke a standalone cargo-dist archive (.tar.xz or .zip): unpack it into a clean directory
# and run the shared fixture-repository loop (fixture-loop.sh) with the unpacked frob.
# Usage: archive-smoke.sh ARCHIVE [EXPECTED_VERSION]   (POSIX sh; Git Bash on Windows)
set -eu

archive="${1:?usage: archive-smoke.sh ARCHIVE [EXPECTED_VERSION]}"
want="${2:-}"
here="$(cd "$(dirname "$0")" && pwd)"
archive="$(cd "$(dirname "$archive")" && pwd)/$(basename "$archive")"
work="$(mktemp -d)"
trap 'cd /; rm -rf "$work"' EXIT

echo "smoke-archive: $(basename "$archive")" >&2
mkdir "$work/unpacked"
case "$archive" in
    *.tar.xz) tar -xJf "$archive" -C "$work/unpacked" ;;
    # Git Bash has no unzip; the runners' python reads zips everywhere.
    *.zip) "$(command -v python3 || command -v python)" -m zipfile -e "$archive" "$work/unpacked" ;;
    *) echo "smoke-archive: unknown archive type: $archive" >&2; exit 1 ;;
esac
exe="$(find "$work/unpacked" \( -name frob -o -name frob.exe \) -type f | head -n 1)"
[ -n "$exe" ] || { echo "smoke-archive: no frob executable in $archive" >&2; exit 1; }
chmod +x "$exe" 2>/dev/null || true
"$here/fixture-loop.sh" "$(dirname "$exe")" "$want"
echo "smoke-archive: ok"
