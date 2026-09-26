## Done report

frob natives build (and the T-1213 land-time auto-rebuild) always spawned
maturin develop for every declared native, 70-190s per land, even when
the worktree's crate tree was byte-identical to an extension already
built elsewhere. _try_reuse_native compares the crate's git-tracked
source digest (_tracked_source_digest, reused from T-4431/T-4434's
worktree-safe digest -- ignores untracked build noise like uv.lock) plus
a rustc --version toolchain id against a stamp recorded the last time
any build succeeded for that crate, stored under the clone's shared
git-common-dir (visible to every worktree). On a match it copies the
previously-built package directory into this root's own site-packages
instead of rebuilding; a digest, toolchain, or undeterminable-toolchain
mismatch always falls through to a real rebuild (fail-closed).

Positive control (measured directly, not just under test): two
consecutive natives-build runs in the same worktree logged "building ...
via maturin develop" then "built cleanly" on the first run, and
"reusing ... -- crate tree digest unchanged" on the second, with no
second maturin spawn; a subsequent merge that changed strata-core/src
(but left frob-core untouched) correctly rebuilt only strata_core and
reused frob_core.

### Changed
```
 docs/modules/cli.md              |  93 ++++++++-----
 frob.lock                        |  20 ++-
 src/frob/natives/_build.py       | 293 +++++++++++++++++++++++++++++++++++++--
 tests/unit/test_natives_build.py | 141 ++++++++++++++++++-
 tickets/T-5808/ticket.md         |   6 +
 5 files changed, 506 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/unit/test_natives_build.py::TestNativeReuse::test_reuses_a_matching_prior_build` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativeReuse::test_digest_mismatch_falls_back_to_a_real_build` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativeReuse::test_toolchain_mismatch_falls_back_to_a_real_build` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativeReuse::test_missing_toolchain_id_never_reuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

### Note: dry-run/land parity gap observed (T-5161)
`frob check --ticket T-5808` reported clean on every ERROR-tier gate for
the touched set across several passes, but the real `frob ticket land`
refused on a SELFAUDIT001 finding (`_build.py`'s new fs.read/fs.write on
the `natives` node, from `_load_reuse_stamps`/`_save_reuse_stamps`) that
never surfaced pre-land through `frob check --ticket`. This is exactly
the gap T-5161 (queued) exists to close -- worth citing as a live
incident when that ticket lands.
