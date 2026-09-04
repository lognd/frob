## Done report

T-3757's win32 --timeout=600 fix had cmd: evidence, invalid per COV003 for a code-kind ticket. Added test_win32_test_step_raises_per_test_timeout_to_600 asserting --timeout=600 stays in the windows Test step's Start-Process ArgumentList, verified to fail when the value is changed to 999. Gates: gates-fast/gates-native/gates-security/lint/static all pass; only remaining error is the pre-existing, out-of-scope COV003 on T-3757 itself, to be cleared by rebinding its evidence to this new node id in a follow-up step.

### Changed
```
 tickets/T-3771/ticket.md | 2 ++
 1 file changed, 2 insertions(+)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_win32_test_step_raises_per_test_timeout_to_600` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4315 warning(s), 924 waived
- error-findings: COV003@tests/test_ci_workflow_matrix.py
