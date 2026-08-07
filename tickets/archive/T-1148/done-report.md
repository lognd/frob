## Done report

Root cause: nothing in the gate pipeline named "declared native fails to
import" as its own, single, fail-fast diagnostic. `stale_natives` (T-0248)
only compares a BUILT native's mtime/content against its source tree,
deliberately treating a completely unbuilt/unimportable native as out of
scope (`_artifact_mtime` returns `None`). `missing_natives` (T-0333) is
TEST-collection-side only. Neither one runs before `run_gates`'s normal
pipeline, so when `strata_core`/`frob_core` fail to import (e.g. a root
`uv sync` reinstalled the package without its compiled extensions, the
2026-07-28 incident), `design/frob.strata` cannot even be parsed and every
gate that resolves an edge/anchor through it reports its own dangling
finding -- the 43 spurious DRIFT002 "no candidates" errors this ticket
cites, one per `design/frob.strata` node, none naming the real cause.

Fix:
- `frob.strata._native_staleness.unimportable_natives(root)`: every
  declared `[[native]]` that fails `importlib.import_module` right now
  (not just `find_spec`, since a partially-installed extension can
  resolve a spec that still fails at actual import time).
- `native_unavailable_warning(root)`: the human message (native names +
  `run: uv run frob natives build`).
- `frob.gates.__init__._native_unavailable_report`: calls the above FIRST
  inside `run_gates`, before `_load_inputs` builds any graph/design/
  ticket state. If any declared native is unimportable, `run_gates`
  returns a `GateReport` with exactly ONE `NATIVE001` ERROR violation and
  skips the rest of the pipeline entirely for that run -- the
  misattributed cascade never has a chance to fire. A healthy checkout
  (every declared native imports, or none are declared) is unaffected:
  `_native_unavailable_report` returns `None` and `run_gates` proceeds
  through its normal multi-gate pipeline exactly as before.
- `NATIVE001` registered in `_KNOWN_GATE_RULES` (frob.gates._waive).
- `docs/modules/gates.md#native001-t-1148`: new section documenting the
  gate, the incident, and why it lives ahead of `_load_inputs`.
- `design/frob.strata`: SYS104 `sync-interface` upkeep (dogfooded --
  `uv run frob sys sync-interface`) for the two new public strata symbols
  and the two new test classes.

Verified directly: constructed a `frob.toml` declaring a native that
cannot import (`frob_definitely_not_a_real_native_xyz`) and confirmed
`run_gates` returns exactly one `NATIVE001` violation naming the fake
native and `uv run frob natives build`, with every other gate skipped
(`tests/test_gates.py::TestNativeAvailabilityGate`). Confirmed the
no-natives-declared case is unaffected (`test_every_native_importable_
runs_the_normal_pipeline`).

Gates run (chunked, --ticket T-1148, after re-merging main to pick up a
concurrently-landed T-1111 the first merge predated):
- gates-fast: clean (0 errors).
- gates-native: clean (0 errors) -- one genuine `frob:waive DUP001`
  needed on `TestUnimportableNatives.test_healthy_native_reports_nothing`
  (95% textually similar to a pre-existing `TestStaleNatives` fixture
  setup, but asserts a different function's contract).
- gates-security: clean (0 errors) -- SELFAUDIT001/SYS104 required the
  `sync-interface` upkeep above.
- lint/static: `ruff check`/`ruff format --check`/`ty check` all pass
  clean on every file this ticket touches.
- `uv run frob sys sync-interface --check`: "no drift -- every interface=
  attr is current".

`git diff main --diff-filter=D --stat` is empty (after the re-merge; the
first diff run flagged `invariants/INV-048.md` as deleted, which was
actually main having advanced past my worktree's merge point via a
concurrently-landed T-1111 -- re-merged main and it resolved cleanly,
confirmed with a second `--diff-filter=D` check).

### Changed
```
 design/frob.strata                         |  4 ++
 docs/modules/gates.md                      | 45 +++++++++++++++++
 frob.lock                                  |  2 +-
 src/frob/gates/__init__.py                 | 52 ++++++++++++++++++-
 src/frob/gates/_waive.py                   |  4 ++
 src/frob/strata/__init__.py                |  4 ++
 src/frob/strata/_native_staleness.py       | 80 ++++++++++++++++++++++++++++++
 tests/test_gates.py                        | 45 +++++++++++++++++
 tests/unit/strata/test_native_staleness.py | 50 +++++++++++++++++++
 tickets.md                                 | 30 ++++++++++-
 10 files changed, 313 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_reports_a_declared_native_that_fails_to_import` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_healthy_native_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_no_declared_natives_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeAvailabilityGate::test_unimportable_native_short_circuits_run_gates_with_one_finding` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeAvailabilityGate::test_every_native_importable_runs_the_normal_pipeline` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
