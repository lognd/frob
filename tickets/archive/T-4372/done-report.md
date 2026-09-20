## Done report

Measured (win4.log) the -n2 windows Test step hitting the old 4500s FROB_TEST_TOTAL_BUDGET_SECONDS cap at 83% of items collected (last progress line before SUITE-RESULT: TOTAL-BUDGET-EXCEEDED at 4500.7s elapsed read [ 83%]); linear extrapolation (4500.7/0.83) projects ~5423s for 100%.

Per T-4372's own preference order: (1) skipping/splitting the frob_self_scan_heavy group would save only its own ~206s (measured solo in T-4360's own notes), far short of the ~900-1200s gap; (2) raising workers back toward -n3/-n4 reopens the OOM T-4360 fixed, with no new memory measurement here to justify it, and is outside this ticket's scope (.github/workflows/*.yml only); so (3) raising the budget with this measured justification is the smallest correct fix.

Raised FROB_TEST_TOTAL_BUDGET_SECONDS 4500 -> 6000 and the outer Wait-Process backstop 4800 -> 6300 (kept ~300s above the internal cap, T-3749's fire-first-with-diagnostic ordering), both comfortably inside the job's timeout-minutes: 150.

Filed T-4382 separately for the COV003 platform-unavailable-evidence mechanism found while reading the same CI run (out of this ticket's own scope).

### Changed
```
 .github/workflows/ci.yml         | 20 ++++++++++++++++++--
 tests/test_ci_workflow_matrix.py | 36 ++++++++++++++++++++++++++++++++++++
 tickets/T-4372/ticket.md         |  2 ++
 3 files changed, 56 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_budget_covers_n2_measured_wall_time` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
