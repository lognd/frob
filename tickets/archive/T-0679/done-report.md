## Done report

T-0636's `is_hard_regression` checked whether the ENTIRE bounded
`HISTORY_WINDOW` history was all-fail. A single stale pass anywhere in
that window (e.g. from before quarantine, or a one-off flake that never
repeated) defeated all-fail detection for up to `HISTORY_WINDOW - 1`
subsequent all-fail runs even though the test had clearly gone permanently
red since -- exactly the gap this ticket's reviewer flagged.

Fix: `is_hard_regression` now trips on EITHER the existing whole-window
all-fail rule OR a new recent-tail-window rule -- its most recent `tail_k`
runs (new module constant `DEFAULT_REGRESSION_TAIL_K = 5`, floored at the
same `_MIN_HISTORY_FOR_REGRESSION = 3` minimum as the whole-window rule)
are all-fail, independent of what came earlier in the window. `tail_k` is
a keyword-only parameter, defaulting to `DEFAULT_REGRESSION_TAIL_K`, and is
forwarded through `hard_regression_alarms` and `evaluate_gate` so a caller
can widen/narrow it; the default keeps the old whole-window behavior as a
strict subset (an all-fail whole window is always also an all-fail tail).

docs/modules/testing.md's Flake quarantine section updated: the public-API
listing block for `is_hard_regression`/`hard_regression_alarms`/
`evaluate_gate` now documents the `tail_k` parameter and
`DEFAULT_REGRESSION_TAIL_K`, and a new "Recent-tail-window widening
(T-0679)" paragraph explains the gap and the fix in the semantics
narrative.

Out of scope, left as noted in T-0636's own Done report (T-0635's scope,
next in this cluster): `frob.testing.__init__` still does not re-export
`is_hard_regression`/`hard_regression_alarms`, and `frob test`'s CLI path
still does not call `track_python_stability`/`evaluate_gate`/
`hard_regression_alarms` automatically.

No files outside the ticket's declared scope
(src/frob/testing/_stability.py, tests/unit/testing/test_stability.py,
docs/modules/testing.md) were touched.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/testing/test_stability.py::TestHardRegression::test_tail_stale` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestHardRegression::test_tail_short` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestHardRegression::test_tail_cfg` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestAlarms::test_hard_alarm_tail` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestGate::test_hard_regress_tail_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
