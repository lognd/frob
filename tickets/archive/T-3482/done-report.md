## Done report

Raised macOS's CI Test-step budget 25m -> 40m (budget=1500 -> 2400) to match
ubuntu's own T-3426 raise -- run 33308245923 was killed at [67%] mid-run
(not hung) on a suite that has grown to 12816 tests, with two prior CLEAN
macOS runs already at 24m/28m. Updated the T-3250/T-3426 comment blocks
in .github/workflows/ci.yml to record the new measurement instead of
stating the stale 25m-is-fine claim.

Evidence:
- FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist tests/unit/test_release_workflow_gate.py:
  exitstatus=0 collected=21 failed=0
- New tests (TestCiUbuntuTestBudgetRaised, extended): macOS budget >= 40m,
  job timeout exceeds the macOS step budget, macOS still uses
  PYTHONFAULTHANDLER + kill -ABRT, and a new cross-platform parity
  assertion (ubuntu and macOS budgets must be numerically equal) so the
  two platforms cannot drift apart again the way this ticket found them.
- Extracted a shared `_assert_step_uses_faulthandler_and_marker` helper
  for the ubuntu/macOS "still uses faulthandler+sigabrt" assertions
  after gate:DUP (DUP001) flagged the two as 95% duplicate.
- `uv run frob check --ticket T-3482`: no finding references
  .github/workflows/ci.yml or tests/unit/test_release_workflow_gate.py;
  every remaining error is pre-existing/repo-wide (unscoped per the
  ticket-scope note).

Filed: none.

### Changed
```
 tickets/T-3482/ticket.md | 6 ++++++
 1 file changed, 6 insertions(+)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_macos_step_budget_at_least_40_minutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_job_timeout_minutes_exceeds_macos_step_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_macos_step_still_uses_faulthandler_and_sigabrt` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_macos_and_ubuntu_step_budgets_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_step_still_uses_faulthandler_and_sigabrt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 14 error(s), 4024 warning(s), 866 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3482, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
