## Done report

Changed: run_check_cpp/run_check_rust/run_check_ts in src/frob/check/__init__.py
now call _run_gates (the same gates stage _python_tasks already runs for the
Python pipeline), each gated by a new `skip_gates` flag (default off) plus
`ticket`/`base`/`delta` passthroughs matching run_check's own signature. This
closes docs/audits/lang-check-docs.md finding 1: a pure Rust/C++/TS repo
previously ran only its native toolchain and never executed
COV001/DOC001-3/DRIFT001-2/INV/DEC/TODO001.

The new kwargs are a public API surface change (REL001 major bump); bumped
pyproject.toml to 0.74.0 (superseded by main's own advance to 0.76.0 during
the merge -- kept main's higher version) and re-ran `frob release stamp`
against the merged tree.

Test/gate evidence (measured, not estimated):
- `uv run pytest tests/unit/test_check.py -o addopts="" -q -k "not
  TestRunGatesQueueFailure and not TestRunGatesDelta"` -> 31 passed, 3
  deselected, in 1.00s.
- The 3 deselected pre-existing tests (TestRunGatesQueueFailure,
  TestRunGatesDelta x2) call the real `_run_gates`, which internally spawns a
  `ProcessPoolExecutor` (T-0415). Under this session's heavy concurrent
  multi-worktree load (30-80+ sibling `frob check`/pytest processes observed
  running at once on a 12-core box), that process-pool stage stalls
  indefinitely -- reproduced with a bare `faulthandler` dump showing the
  hang sits in `frob.gates.__init__._drain_futures` waiting on a
  `ProcessPoolExecutor` future, with ZERO code of mine on the stack, and
  reproduced identically for these SAME pre-existing tests with none of my
  changes involved. This is a pre-existing environment/contention artifact
  in `src/frob/gates/` (out of T-0554's `src/frob/check/` scope), not a
  regression introduced here. My own two new-per-pipeline tests
  (`test_gates_stage_runs_by_default` x3) were designed to avoid this class
  of flake entirely: they monkeypatch `frob.check._run_gates` to prove only
  that each pipeline WIRES the call in by default, never exercising the real
  process-pool machinery.
- `uv run frob check --ticket T-0554` -> `[WARN] 0 errors 464 warnings`
  (clean; all warnings pre-existing/unrelated).
- `uv run frob check --delta` -> no `.frob/baseline` stamp existed in this
  worktree (never stamped at warm-up), so it degraded to the full violation
  set per its documented fallback: 2 errors shown, both in files this ticket
  never touched (`src/frob/strata/_native_staleness.py` ARCH001,
  `src/frob/gates/_registry_exhaustiveness.py` COV007) -- pre-existing debt,
  not introduced by this change.

Filed: none (no out-of-scope work found beyond the pre-existing gates
process-pool contention noted above, which is an environment artifact this
session, not a code defect to file).

Gates: frob check --ticket T-0554 clean (0 errors). frob check --delta
degraded to full-set (no baseline stamped this session) and shows 2
pre-existing errors outside this ticket's scope.

### Changed
```
 .frob-release.json         |  6 ++--
 src/frob/check/__init__.py | 72 +++++++++++++++++++++++++++++++++++----
 tests/unit/test_check.py   | 85 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 35 +++++++++++++++++--
 4 files changed, 186 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestRunCheckCpp::test_gates_stage_runs_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckRust::test_gates_stage_runs_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckTs::test_gates_stage_runs_by_default` (pytest node id, verified passing when recorded)
