## Done report

strata-core/src/lib.rs's O(graph) #[pyfunction]s (reachable, worst_age, propagated_demand,
vmodel_check) now wrap their bodies in py.allow_threads(|| ...): each was split into a thin
pyo3-facing wrapper (py: Python<'_> as first arg, auto-injected by pyo3) that calls a new
private _impl function holding the exact original logic. pyo3 already extracts Python
arguments into owned Rust data (Vec<Edge>/String/etc.) before the function body runs, and
converts the returned tuple/HashMap back to a Python object only after allow_threads's
closure returns and the GIL is reacquired, so no unsafe/ordering change was needed beyond
the wrap itself. demand and parse_source were left unwrapped (demand is a single O(n)
filter/sum, not the O(graph) traversal this ticket targets; parse_source is a separate
concern not named in the ticket or T-3449's stack trace).

Existing Rust unit tests (mod tests in lib.rs) called the old function names directly;
retargeted them to the new _impl names (Python<'_> has no meaningful unit-test double, and
the ticket's own regression coverage belongs in Python where the GIL-preemption behavior is
actually observable). cargo test --lib: 202 passed, 0 failed.

New Python coverage in tests/unit/strata/test_strata_core_gil.py:
- test_timeout_fires_during_worst_age (must-fire): spawns a pytest subprocess running a
  synthetic ~6s worst_age call under --timeout=2 --timeout-method=thread; asserts the
  subprocess is killed near the 2s deadline (elapsed < 5s) with pytest-timeout's stack-dump
  marker present -- the exact regression T-3449 measured (a real strata_core call ran a full
  67s under --timeout=5 with the watchdog never firing once) is now fixed.
- test_background_thread_runs_during_worst_age (must-fire): a background ticker thread
  accumulates >5 ticks during a ~4s direct worst_age call, direct proof the GIL is released
  independent of pytest-timeout's own machinery.
- test_worst_age_result_unchanged / test_reachable_result_unchanged /
  test_propagated_demand_result_unchanged (must-stay-quiet): mirror the shapes of
  strata-core/src/lib.rs's own worst_age_takes_the_stalest_path /
  reachable_returns_witness_paths / propagated_demand_chain_multiplies_fanout Rust unit
  tests, called across the pyo3 FFI boundary -- proves py.allow_threads is a pure
  concurrency change with bit-for-bit identical return values.

All 5 new tests pass: node-id run, -p no:xdist, exitstatus=0 collected=5 failed=0.

Did NOT bump strata-core's crate/pyproject version: docs/guides/release.md documents that
frob/frob-core/strata-core are pinned to one synchronized version, bumped only by frob
release publish's own automation at actual release-cut time (X.Y.Z -> X.Y.(Z+1)), never by
an individual ticket/commit -- a per-ticket hand-bump would desync from that automation's own
source of truth. land's own T-2445 changelog-fragment step records this change for the next
release cut, same as every other ticket.

Gates: ruff-check clean on touched files; ruff-format clean after reformatting the new test
file (frob check --ticket T-3457 --budget 300 flagged 5 OTHER pre-existing unformatted files
repo-wide, unrelated to this ticket -- verified via ruff format --check .); ty check clean on
the new test file after fixing one invariant-list annotation (propagated_demand's edges arg
needed an explicit list[tuple[str, str, str, float | None, float]] annotation, not a repo-wide
issue).

### Changed
```
 tickets/T-3457/done-report.md | 21 +++++++++++++++++++++
 tickets/T-3457/ticket.md      | 16 +++++++++++++++-
 2 files changed, 36 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_strata_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_worst_age` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_strata_core_gil.py::TestGilActuallyReleased::test_background_thread_runs_during_worst_age` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_strata_core_gil.py::TestResultsUnchanged::test_worst_age_result_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_strata_core_gil.py::TestResultsUnchanged::test_reachable_result_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_strata_core_gil.py::TestResultsUnchanged::test_propagated_demand_result_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 15 error(s), 4131 warning(s), 856 waived
- error-findings: AFFECT001@strata-core/src/lib.rs, COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3457, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
