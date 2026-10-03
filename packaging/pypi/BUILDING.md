# Building the PyPI wheel

Not shipped in the wheel. The wheel is a maturin `bindings = "bin"` build of the
`frob-cli` package (binary `frob`); `grimble` is built by cargo and added through
maturin's `data` directory (`data/scripts/`, git-ignored, filled by the script).

## Local build (this host)

    packaging/pypi/build-wheel.sh [--out DIR]     # default DIR: target/wheels

Needs `uv` and a Rust toolchain. On Linux it asks maturin for `manylinux_2_28`
and fails if the host glibc is newer than that allows; either build in the
manylinux container (below) or set `WHEEL_COMPAT=off` to accept the host tag
(a local smoke wheel only, never published; `smoke.sh` then also skips the
manylinux tag check).

## manylinux_2_28 in the container (what the release job must do)

    docker run --rm -v "$PWD":/work -w /work \
      -e CARGO_TARGET_DIR=/work/target/m28 \
      -e CARGO_TARGET_<TRIPLE>_LINKER=gcc -e RUSTFLAGS="-C debuginfo=0" \
      quay.io/pypa/manylinux_2_28_<arch> bash -c \
      'curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal;
       export PATH=$HOME/.cargo/bin:/opt/python/cp312-cp312/bin:$PATH;
       pip install uv; packaging/pypi/build-wheel.sh --out /work/target/m28/wheels'

`.cargo/config.toml` links with clang and mold, which the image lacks, hence the
linker and `RUSTFLAGS` overrides (an env `RUSTFLAGS` replaces the config's).
Measured 2026-10-03 on aarch64: about 3 minutes cold; wheel
`frob-VERSION-py3-none-manylinux_2_28_aarch64.whl`, about 42 MB unpacked.

## Release workflow wheel job (ticket 5Y75MX7)

`.github/workflows/release.yml` job `wheel`, one matrix entry per target; wheels are
run artifacts (`wheel-<target>`), nothing is published there.

- Linux x86_64 / aarch64: native runners (`ubuntu-latest`, `ubuntu-24.04-arm`), the
  digest-pinned `quay.io/pypa/manylinux_2_28_<arch>` image via `docker run` as above.
- macOS arm64: `macos-latest`. macOS x86_64: `macos-latest` with
  `build-wheel.sh --target x86_64-apple-darwin` (cargo and maturin both get the target).
  The arm64 runner cannot execute it, so it is the single smoke exemption
  (`smoke: false`; pinned by `crates/frob-release/tests/release_workflow.rs`).
- Windows x86_64: `windows-latest`, Git Bash; `build-wheel.sh` and `smoke.sh` use the
  venv's `Scripts/` directory there.
- maturin is pinned exactly (`MATURIN_VERSION` in the workflow, passed through to
  `build-wheel.sh`); no hash pin. Every other smoked wheel runs
  `smoke.sh WHEEL VERSION` on its build runner.
- No sdist is built (see the last bullet).

## Still to decide / other tickets

- Build the wheel from the tagged commit; the version is the static
  `[project] version` that `frob release cut` rewrites (REL002 checks it).
- `maturin sdist` is allowed but needs the whole workspace; build it from the
  repository root path `packaging/pypi` only after deciding to ship one.
- Publish only in the protected release environment (`uv publish`), after smoke.

## Smoke

`packaging/pypi/smoke.sh WHEEL [VERSION]` installs the wheel into a clean venv, runs
`frob --version` and `grimble --version`, then runs `packaging/smoke/fixture-loop.sh`:
a throwaway git repository with a tiny crate and a markdown file goes through `frob init`,
`doctor`, `check`, `ticket new` (one criterion), `work`, an edit, `check --ticket`, command
provider evidence, a changelog fragment named with the ticket id, `land`, then asserts the
ticket is closed done and `ticket doctor` is clean. It needs git and cargo, uses only the
installed binaries, and is POSIX sh. Standalone archives run the same loop through
`packaging/smoke/archive-smoke.sh ARCHIVE [VERSION]`.
