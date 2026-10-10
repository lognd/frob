# Building the PyPI wheels

Not shipped in the wheels. PyPI gets one wheel set per product (D87): `frob`, `grimble` and `crunk`,
each a maturin `bindings = "bin"` build of that product's Cargo package and carrying only its
own binary. `frob`'s wheel requires `grimble==<same version>`, so installing `frob` pulls
`grimble` and installing `grimble` alone installs only `grimble`; `crunk` likewise installs alone.

### Gates on crunk

- `frob`'s wheel depends on `crunk` only from the first crunk preview release (~AYA6294); until
  then `frob` depends on `grimble` alone. `products.rs` pins the current set, so adding the
  dependency is a deliberate test change in that release ticket.
- The crunk wheel is uploaded with the others from 0.533.0: the Rust crunk supersedes the
  Python crunk (lognd/crunk, 0.1.x) as the PyPI project `crunk` (owner decision 2026-10-09,
  lifting the D87 hold-back; docs/design/README.md D135). The `crunk` project must trust this
  repository's `release.yml` with environment `pypi`.

The product list is `products.toml` (name, Cargo package and manifest, summary, keywords,
dependencies). `render.py` turns each entry into a maturin project (`pyproject.toml`,
`README.md`, `LICENSE`) under `target/pypi/<product>` from `pyproject.template.toml` and
`readme.template.md`; nothing per product is copied or checked in. The version is the Cargo
lockstep version (`frob-cli`) read at render time, so every wheel and the `grimble==` pin equal
it by construction and `frob release bump` has no Python metadata to edit. Adding a product
(crunk was the last) is one more `[[product]]` table, one more name in the
workflow count loops (`for product in frob grimble crunk`, pinned by
`crates/frob-release/tests/products.rs`) and the archive/dist entries of products.md 6.

## Local build (this host)

    cargo dev wheel [--out DIR] [--target TRIPLE] [--product NAME]...   # default DIR: target/wheels, all products

Needs `uv`, Python 3.11+ (uv finds one) and a Rust toolchain. On Linux it asks maturin for `manylinux_2_28`
and fails if the host glibc is newer than that allows; either build in the
manylinux container (below) or set `WHEEL_COMPAT=off` to accept the host tag
(a local smoke wheel only, never published; `cargo dev wheel-smoke` then also skips the
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
       pip install uv; cargo dev wheel --out /work/target/m28/wheels'

`.cargo/config.toml` links with clang and mold, which the image lacks, hence the
linker and `RUSTFLAGS` overrides (an env `RUSTFLAGS` replaces the config's).
Measured 2026-10-03 on aarch64: about 3 minutes cold for the frob wheel
`frob-VERSION-py3-none-manylinux_2_28_aarch64.whl` (about 42 MB unpacked when it still bundled
grimble); the grimble wheel is built the same way after it.

## Release workflow wheel job (ticket 5Y75MX7)

`.github/workflows/build-smoke.yml` job `wheel` (the reusable workflow `release.yml` calls
with `wheels: true`), one matrix entry per target, each building every product's wheels; the set is one
run artifact (`wheel-<target>`), nothing is published there.

- Linux x86_64 / aarch64: native runners (`ubuntu-latest`, `ubuntu-24.04-arm`), the
  digest-pinned `quay.io/pypa/manylinux_2_28_<arch>` image via `docker run` as above.
- macOS arm64: `macos-latest`. macOS x86_64: `macos-latest` with
  `cargo dev wheel --target x86_64-apple-darwin` (cargo and maturin both get the target).
  The arm64 runner cannot execute it, so it is the single smoke exemption
  (`smoke: false`; pinned by `crates/frob-release/tests/release_workflow.rs`).
- Windows x86_64: `windows-latest`; `cargo dev wheel` and `cargo dev wheel-smoke` pick the
  venv's `Scripts\python.exe` layout in Rust, so no shell, `realpath` or `uname` is involved
  (a GNU-only `realpath -m` and a bare `Scripts/python` broke the shell script on macOS and
  Windows, ticket 1T8TCTA).
- maturin is pinned by version and sha256 in `maturin-requirements.txt`, which
  `cargo dev wheel` installs with `uv pip install --require-hashes --no-deps`.
- rustup-init in the containers is `RUSTUP_INIT_VERSION` downloaded from
  `static.rust-lang.org/rustup/archive/<ver>/<triple>/rustup-init` and verified against
  the matrix's `rustup_sha` (the published `rustup-init.sha256` of that version and
  triple) before it runs. To bump either pin, fetch the new hashes (rustup: the `.sha256`
  next to the binary; maturin: PyPI JSON `urls[].digests.sha256`) and change them with the
  version in one commit; `release_workflow.rs` fails on a missing check.
- Every other target's wheel set is smoked with
  `cargo dev wheel-smoke target/wheels VERSION` on its build runner, and again on a fresh runner in `smoke`.
- No sdist is built, by decision: the wheel bundles prebuilt binaries, an sdist would need
  the whole workspace, and source ships through crates.io and git (releases.md 6).

## Still to decide / other tickets

- Build the wheels from the tagged commit; the version is the Cargo lockstep version that
  `frob release cut` rewrites, read by `render.py` at build time.
- No sdist (decided, releases.md 6): `maturin sdist` would need the whole workspace and
  would add an unsmoked source-build path; revisit only by changing that decision.
- Publish only in the protected `pypi` environment (the `pypi` job, pypa/gh-action-pypi-publish via trusted publishing, one PyPI project per product, five wheels each checked before upload), after smoke (the `smoke` job
  re-runs `cargo dev wheel-smoke` on a fresh runner against the downloaded wheels; publishing jobs need it).

## Smoke

`cargo dev wheel-smoke WHEEL_DIR [VERSION]` (crates/gob-dev/src/wheel_smoke.rs) checks each wheel's metadata (name, platform
tag, only its own binary, the `grimble==` pin), then installs from the directory only
(`--no-index --find-links`, never the index) in four scenarios: (a) grimble alone into a clean
venv, which installs only grimble; (b) frob alone into a clean venv, which pulls grimble at
the same version, then runs both and the fixture loop below; (c) `uv tool install frob`, where
grimble is not on `PATH` and `frob doctor` still reports it `beside-frob` (on Windows through the tool environment under `UV_TOOL_DIR`, because uv copies `frob.exe` into the bin directory), then `frob check`; (d) crunk alone into a clean venv, which installs only crunk.
The loop of (b) is `packaging/smoke/fixture-loop.sh`:
a throwaway git repository with a tiny crate and a markdown file goes through `frob init`,
`doctor`, `check`, `ticket new` (one criterion), `work`, an edit, `check --ticket`, command
provider evidence, a changelog fragment named with the ticket id, `land`, then asserts the
ticket is closed done and `ticket doctor` is clean. It needs git and cargo, uses only the
installed binaries, and is POSIX sh (the one remaining script, shared with the archive smoke; `wheel-smoke` runs it through `sh`). Standalone archives run the same loop through
`packaging/smoke/archive-smoke.sh ARCHIVE [VERSION]`.
