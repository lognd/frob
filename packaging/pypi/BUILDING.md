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
      'curl -sSfo /tmp/rustup-init https://static.rust-lang.org/rustup/archive/<ver>/<triple>/rustup-init;
       echo "<sha256>  /tmp/rustup-init" | sha256sum -c -;
       chmod +x /tmp/rustup-init; /tmp/rustup-init -y --profile minimal;
       export PATH=$HOME/.cargo/bin:/opt/python/cp312-cp312/bin:$PATH;
       pip install uv; packaging/pypi/build-wheel.sh --out /work/target/m28/wheels'

`.cargo/config.toml` links with clang and mold, which the image lacks, hence the
linker and `RUSTFLAGS` overrides (an env `RUSTFLAGS` replaces the config's).
Measured 2026-10-03 on aarch64: about 3 minutes cold; wheel
`frob-VERSION-py3-none-manylinux_2_28_aarch64.whl`, about 42 MB unpacked.

## Release workflow wheel job (ticket 5Y75MX7)

`.github/workflows/build-smoke.yml` job `wheel` (the reusable workflow `release.yml` calls
with `wheels: true`), one matrix entry per target; wheels are
run artifacts (`wheel-<target>`), nothing is published there.

- Linux x86_64 / aarch64: native runners (`ubuntu-latest`, `ubuntu-24.04-arm`), the
  digest-pinned `quay.io/pypa/manylinux_2_28_<arch>` image via `docker run` as above.
- macOS arm64: `macos-latest`. macOS x86_64: `macos-latest` with
  `build-wheel.sh --target x86_64-apple-darwin` (cargo and maturin both get the target).
  The arm64 runner cannot execute it, so it is the single smoke exemption
  (`smoke: false`; pinned by `crates/frob-release/tests/release_workflow.rs`).
- Windows x86_64: `windows-latest`, Git Bash; `build-wheel.sh` and `smoke.sh` use the
  venv's `Scripts/` directory there.
- maturin is pinned by version and sha256 in `maturin-requirements.txt`, which
  `build-wheel.sh` installs with `uv pip install --require-hashes --no-deps`.
- rustup-init in the containers is `RUSTUP_INIT_VERSION` downloaded from
  `static.rust-lang.org/rustup/archive/<ver>/<triple>/rustup-init` and verified against
  the matrix's `rustup_sha` (the published `rustup-init.sha256` of that version and
  triple) before it runs. To bump either pin, fetch the new hashes (rustup: the `.sha256`
  next to the binary; maturin: PyPI JSON `urls[].digests.sha256`) and change them with the
  version in one commit; `release_workflow.rs` fails on a missing check.
- Every other smoked wheel runs
  `smoke.sh WHEEL VERSION` on its build runner.
- No sdist is built, by decision: the wheel bundles prebuilt binaries, an sdist would need
  the whole workspace, and source ships through crates.io and git (releases.md 6).

## Still to decide / other tickets

- Build the wheel from the tagged commit; the version is the static
  `[project] version` that `frob release cut` rewrites (REL002 checks it).
- No sdist (decided, releases.md 6): `maturin sdist` would need the whole workspace and
  would add an unsmoked source-build path; revisit only by changing that decision.
- Publish only in the protected `pypi` environment (the `pypi` job, pypa/gh-action-pypi-publish via trusted publishing), after smoke (the `smoke` job
  re-runs `smoke.sh` on a fresh runner against the downloaded wheel; publishing jobs need it).

## Smoke

`packaging/pypi/smoke.sh WHEEL [VERSION]` installs the wheel into a clean venv, runs
`frob --version` and `grimble --version`, then runs `packaging/smoke/fixture-loop.sh`:
a throwaway git repository with a tiny crate and a markdown file goes through `frob init`,
`doctor`, `check`, `ticket new` (one criterion), `work`, an edit, `check --ticket`, command
provider evidence, a changelog fragment named with the ticket id, `land`, then asserts the
ticket is closed done and `ticket doctor` is clean. It needs git and cargo, uses only the
installed binaries, and is POSIX sh. Standalone archives run the same loop through
`packaging/smoke/archive-smoke.sh ARCHIVE [VERSION]`.
