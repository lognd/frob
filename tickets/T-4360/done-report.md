## Done report

Evidence: tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_caps_workers_at_n2
(pytest node id bound via `frob ticket evidence`). This is a
workflow-content assertion, not a repro of the OOM itself -- the
underlying claim is measurement, documented in
tickets/T-4360/measurement-notes.md, rooted in gh run 34315257799
(job 102350012616), where two frob_self_scan_heavy-group workers each
died independently ~300s in with no timeout dump ("suspect OOM"),
consistent with Candidate 3 (single scan + ambient `-n auto` fanout
exceeds real Windows-runner headroom). Fix is NOT yet confirmed by
repeated green runs -- per the Consecutive-completions bar in
measurement-notes.md, this needs at least 3 consecutive non-OOM-
aborted Windows CI completions post-change before being called a
confirmed fix, not just a measured hypothesis.
Filed: none
Gates: uv run frob check --ticket T-4360 clean (gate:TICK's only error,
TICK010, is a pre-existing repo-wide finding about T-4346's stale
lease, unrelated to this ticket's scope)

### Changed
```
 .github/workflows/ci.yml            |  29 ++++++++-
 tests/test_ci_workflow_matrix.py    |  23 +++++++
 tickets/T-4360/measurement-notes.md | 122 ++++++++++++++++++++++++++++++++++++
 tickets/T-4360/ticket.md            |   2 +
 4 files changed, 175 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_caps_workers_at_n2` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4764 warning(s), 965 waived
- error-findings: TICK010@/home/logan/projects/frob/.git/frob-leases/T-4346.json
