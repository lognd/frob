# Building the PyPI wheel

Not shipped in the wheel. The wheel is a maturin `bindings = "bin"` build of the
`frob-cli` package (binary `frob`); `grimble` is built by cargo and added through
maturin's `data` directory (`data/scripts/`, git-ignored, filled by the script).

## Local build (this host)

    packaging/pypi/build-wheel.sh [--out DIR]     # default DIR: target/wheels

Needs `uv` and a Rust toolchain. On Linux it asks maturin for `manylinux_2_28`
and fails if the host glibc is newer than that allows; either build in the
manylinux container (below) or set `WHEEL_COMPAT=off` to accept the host tag
(a local smoke wheel only, never published).

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

## What ticket 5Y75MX7 (workflow wheel matrix) needs

- Linux x86_64 and aarch64 (smoke.sh WHEEL VERSION after each build): the container above (no cross compile needed; use
  native runners for each arch). The wheel is not abi-specific (`py3-none`).
- macOS arm64 and x86_64: `macos-latest`; for x86_64 add the rust target
  `x86_64-apple-darwin` and pass `--target x86_64-apple-darwin`. `build-wheel.sh`
  does not take a target yet: extend it with `--target T` that is forwarded to the
  `cargo build -p grimble` and to `maturin build`, and copy grimble from
  `target/T/release`.
- Windows x86_64: `grimble.exe` is handled by the script (`OS=Windows_NT`), but
  the venv path is `Scripts/` there and `install -m` needs Git Bash; verify.
- Every build job: pinned maturin (the script pins `>=1.9,<2`; pin an exact version
  with a hash in the workflow), a timeout, and artifact smoke after the build:
  `uv venv; uv pip install <wheel>; frob --version; grimble --version; frob doctor`
  in a fixture repository (ticket NWXQPMM).
- Build the wheel from the tagged commit; the version is the static
  `[project] version` that `frob release cut` rewrites (REL002 checks it).
- `maturin sdist` is allowed but needs the whole workspace; build it from the
  repository root path `packaging/pypi` only after deciding to ship one.
- Publish only in the protected release environment (`uv publish`), after smoke.
