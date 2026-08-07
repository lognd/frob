## Done report

T-0575 landed `frob.testing._stability` (record_outcomes, evaluate_gate,
quarantine, alarms) but nothing in `frob test`'s CLI path called it --
tracking only happened if invoked programmatically. This wires it in.

`src/frob/app/test_runner.py` gets a new `_track_python_stability_and_gate`
helper, called from `_run_selected_and_report` right after `run_selected`
returns. For a concrete python selection (`report.selected["python"]`,
skipped when empty or the `ALL_SENTINEL` "*" whole-suite marker, since
neither names per-test node ids to track against) it:

- captures per-test pass/fail via `capture_python_outcomes` and persists it
  via `record_outcomes` (`.frob/test-stability.json` now updates on every
  concrete-selection `frob test` run, not just a programmatic call);
- applies `evaluate_gate` to just the python portion of the run's outcome,
  isolated from any other language's outcomes (a real non-python failure
  is never masked -- proven by `test_other_language_failure_not_masked`);
- logs a warning for every `quarantine_alarms` (closed-ticket-still-flaky)
  and `hard_regression_alarms` (quarantined-but-now-permanently-failing,
  T-0636/T-0679) hit.

Also closed the re-export gap T-0636's Done report disclosed:
`frob.testing.__init__` now re-exports `is_hard_regression`,
`hard_regression_alarms`, and `DEFAULT_REGRESSION_TAIL_K` alongside the
rest of the module's public API.

docs/modules/testing.md's Flake quarantine section gets a new "CLI wiring
(T-0635...)" paragraph explaining the wiring and its known cost (a second,
independent pytest invocation per `frob test` run, since `RunnerOutcome`
does not carry per-test results -- teaching it to is left as future work
if the double-run cost becomes a real problem, not hidden as free).

Known/disclosed gate state: `frob check --ticket T-0635`'s gates-fast pass
shows 2 SCOPE001 errors on docs/modules/testing.md and
tests/unit/testing/test_stability.py. Both are a stacked-ticket artifact,
not real out-of-scope work: T-0679 (recent-tail-window is_hard_regression)
is committed on this same branch ahead of T-0635 and is still
`in-progress` (I do not close tickets myself, per dispatch instructions),
so its scope lease on those two files is still held -- `frob ticket scope
T-0635 --add docs/modules/testing.md` refuses with `ScopeLeaseConflict:
requested --add glob overlaps a path leased by another in-progress
ticket`. T-0635's own actual edit to docs/modules/testing.md is limited to
the new CLI-wiring paragraph; tests/unit/testing/test_stability.py is
untouched by T-0635 at all -- SCOPE001 is diffing the whole branch against
main, which includes T-0679's already-reported, already-evidenced commit.
This should clear once the coordinator closes T-0679 (releasing its lease)
or lands both tickets. lint, static, gates-native, and gates-security all
pass with 0 errors for T-0635 as recorded; gates-fast's only errors are
the two SCOPE001 findings above.

### Changed
```
 docs/modules/testing.md              | 52 +++++++++++++++------
 src/frob/testing/_stability.py       | 91 ++++++++++++++++++++++++++----------
 tests/unit/testing/test_stability.py | 63 +++++++++++++++++++++++++
 tickets.md                           | 61 +++++++++++++++++++++++-
 4 files changed, 227 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/test_app.py::TestStabilityGate::test_quarantined_failure_promotes_to_ok` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestStabilityGate::test_hard_regressed_quarantine_stays_failed` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestStabilityGate::test_other_language_failure_not_masked` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestStabilityGate::test_all_sentinel_selection_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestStabilityGate::test_empty_python_selection_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestStabilityGate::test_capture_error_skips_gate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
