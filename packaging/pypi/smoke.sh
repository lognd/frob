#!/usr/bin/env bash
# Smoke the built wheel set (one wheel per product, D87) from the local wheels only: every
# install uses --no-index --find-links WHEEL_DIR, never the network index. Three scenarios:
#   a. grimble alone: only grimble is installed, and it runs;
#   b. frob alone into a clean venv: grimble at the same version comes with it, both run, and
#      the fixture repository loop (init through land) passes with the installed binaries;
#   c. `uv tool install frob`: only frob is exposed on PATH, and frob still finds grimble
#      beside itself (`frob doctor` reports it as beside-frob) and `frob check` runs.
# Also checks each wheel's metadata (name, platform tag, frob's grimble==VERSION pin, and that
# each wheel carries only its own binary).
# Usage: smoke.sh WHEEL_DIR [EXPECTED_VERSION]   (the repository loop is packaging/smoke/fixture-loop.sh)
set -euo pipefail

dir="$(realpath "${1:?usage: smoke.sh WHEEL_DIR [EXPECTED_VERSION]}")"
want="${2:-}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
say() { echo "smoke: $*" >&2; }
die() { echo "smoke: FAIL: $*" >&2; exit 1; }

# venv layout: Scripts/ on Windows, bin/ elsewhere. Wheels are read with python (zipfile)
# because Git Bash on Windows has no unzip.
sub=bin; exe=""
if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* || "${OS:-}" == "Windows_NT" ]]; then sub=Scripts; exe=".exe"; fi
uv venv -q "$work/reader"
py="$work/reader/$sub/python"

one_wheel() { # the single wheel of product $1 in the wheel dir
    local found=("$dir/$1"-*.whl)
    [[ ${#found[@]} -eq 1 && -f "${found[0]}" ]] || die "expected exactly one $1 wheel in $dir, found: ${found[*]}"
    printf '%s\n' "${found[0]}"
}
wheel_info() { # wheel, then METADATA | WHEEL | SCRIPTS (the executables it installs)
    "$py" -c 'import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
what = sys.argv[2]
if what == "SCRIPTS":
    for n in z.namelist():
        if ".data/scripts/" in n and not n.endswith("/"):
            print(n.rsplit("/", 1)[1])
else:
    name = next(n for n in z.namelist() if n.endswith(".dist-info/" + what))
    sys.stdout.write(z.read(name).decode())' "$1" "$2" | tr -d '\r'
}

# 0. Metadata of each wheel: name, tag, only its own binary; frob pins grimble at its own version.
for product in frob grimble; do
    w="$(one_wheel "$product")"
    tag="$(wheel_info "$w" WHEEL | sed -n 's/^Tag: //p')"
    say "wheel $(basename "$w") tag=$tag"
    wheel_info "$w" METADATA | grep -qx "Name: $product" || die "$w: metadata name is not $product"
    if [[ "$(uname -s)" == Linux && "${WHEEL_COMPAT:-}" != off && "$tag" != *manylinux_2_28* ]]; then
        die "$w: linux tag is not manylinux_2_28 ($tag)"
    fi
    scripts="$(wheel_info "$w" SCRIPTS | sed 's/\.exe$//' | sort | tr '\n' ' ')"
    [[ "$scripts" == "$product " ]] || die "$w carries [$scripts], expected only $product"
done
fver="$(wheel_info "$(one_wheel frob)" METADATA | sed -n 's/^Version: //p')"
wheel_info "$(one_wheel frob)" METADATA | grep -qx "Requires-Dist: grimble==$fver" \
    || die "frob wheel does not require grimble==$fver"

installed() { # venv dir: the installed distribution names, one per line
    uv pip freeze --python "$1/$sub/python" | sed -n 's/^\([A-Za-z0-9_.-]*\)==.*/\1/p'
}
install_args=(--no-index --find-links "$dir")
check_version() { # tool output "name X" against the expected version
    local got="$1" name="$2"
    [[ -z "$want" || "$got" == "$name $want" ]] || die "expected '$name $want', got '$got'"
}

# a. grimble alone.
uv venv -q "$work/a"
uv pip install -q --python "$work/a/$sub/python" "${install_args[@]}" grimble
[[ "$(installed "$work/a")" == grimble ]] || die "a: expected only grimble, got: $(installed "$work/a" | tr '\n' ' ')"
[[ ! -e "$work/a/$sub/frob$exe" ]] || die "a: grimble alone installed frob"
got="$("$work/a/$sub/grimble" --version | tr -d '\r')"; echo "$got"; check_version "$got" grimble
say "a ok: grimble alone"

# b. frob alone: grimble comes from the same wheel directory at the same version.
uv venv -q "$work/b"
uv pip install -q --python "$work/b/$sub/python" "${install_args[@]}" frob
[[ "$(installed "$work/b" | sort | tr '\n' ' ')" == "frob grimble " ]] || die "b: expected frob and grimble, got: $(installed "$work/b" | tr '\n' ' ')"
got="$("$work/b/$sub/frob" --version | tr -d '\r')"; echo "$got"; check_version "$got" frob
gotg="$("$work/b/$sub/grimble" --version | tr -d '\r')"; echo "$gotg"
[[ "${gotg#grimble }" == "${got#frob }" ]] || die "b: grimble version differs from frob: '$gotg' vs '$got'"
# The shared fixture-repository loop (init through land) with the installed binaries.
"$(dirname "$0")/../smoke/fixture-loop.sh" "$work/b/$sub" "$want"
say "b ok: frob pulled grimble at the same version"

# c. uv tool install frob: grimble is not on PATH, and frob finds it beside itself.
export UV_TOOL_DIR="$work/c/tools" UV_TOOL_BIN_DIR="$work/c/bin"
uv tool install -q "${install_args[@]}" frob
[[ -e "$work/c/bin/frob$exe" ]] || die "c: uv tool install exposed no frob"
[[ ! -e "$work/c/bin/grimble$exe" ]] || die "c: grimble is exposed on PATH by the tool install"
(
    PATH="$work/c/bin:$PATH"
    if command -v grimble >/dev/null 2>&1; then die "c: a grimble is already on PATH ($(command -v grimble)); the scenario needs none"; fi
    repo="$work/c/repo"; mkdir -p "$repo"; cd "$repo"
    git init -q; git symbolic-ref HEAD refs/heads/main
    doctor="$(frob --json doctor)"
    case "$doctor" in
        *'"location":"beside-frob"'*'"product":"grimble"'* | *'"product":"grimble"'*'"location":"beside-frob"'*) ;;
        *) die "c: frob doctor did not find grimble beside frob: $doctor" ;;
    esac
    case "$doctor" in *'"product":"grimble","version":"grimble '*) ;; *) die "c: frob doctor could not run the grimble it found" ;; esac
    frob --json init >/dev/null
    out="$(frob --json check)"
    case "$out" in *'"ok":true'*) ;; *) die "c: frob check failed: $out" ;; esac
)
say "c ok: uv tool install frob finds grimble without it on PATH"
say "ok"
