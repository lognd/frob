## Done report

Added the matching `# ty: ignore[unresolved-attribute]` comment alongside
the existing `# type: ignore[attr-defined]` on
src/frob/gates/_debt_deprecated.py:663, matching the canonical dual-dialect
comment order already used elsewhere in the repo (e.g.
src/frob/perf/_heat.py:131). Confirmed the exact ty rule code by running
`uv run ty check src/frob/gates/_debt_deprecated.py` before editing:
`error[unresolved-attribute]` on that line. Did not touch the existing
mypy suppression -- it stays load-bearing for downstream mypy users.

Verified `timeout 540 uv run frob check --only suppress` reports 0 errors,
0 warnings after the change.

Evidence binds both the SUPPRESS001 gate test that covers this dual-
dialect pattern and the existing TestDepr005ViolationsGrowth class
(frob:ticket T-1338), which exercises `_depr005_edge_violations` -- the
function containing the touched line -- directly at gate level.

### Changed
```
 src/frob/gates/_debt_deprecated.py |  2 +-
 tickets.md                         | 36 +++++++++++++++++++++++++++++++++++-
 2 files changed, 36 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_two_baselined_symbols_each_evaluated_independently` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 420 warning(s), 688 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-1357, TICK003@tickets.md
