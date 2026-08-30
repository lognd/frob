## Done report

Raised ubuntu Test step budget in ci.yml from 'timeout -s ABRT 25m' to 40m, and job-level timeout-minutes from 45 to 60 so the step's own instrumented budget (with a faulthandler stack dump) still fires before the bare job ceiling. Updated the T-3192/T-3250 comment blocks that stated the old numbers, citing the T-3426 measurement (run 33277131782: ubuntu reached 99% at ~20m, still inside two whole-repo self-scan test bodies, before the 25m ABRT timeout killed it at 22:18:23; macOS completed the identical suite in 18m31s in the same run). macOS/Windows budgets left at 25m per the ticket's own instruction (no equivalent problem measured there). Added TestCiUbuntuTestBudgetRaised to tests/unit/test_release_workflow_gate.py: MUST-FIRE asserts the ubuntu step budget is >=40m and the job ceiling exceeds it; MUST-STAY-QUIET asserts PYTHONFAULTHANDLER=1 and timeout -s ABRT are still present on the ubuntu step. Follow-up (self-scan tests sharing one cached graph per session) is noted in the ticket body as filed under a future ticket, not done here.

### Changed
```
 .github/workflows/ci.yml                 | 36 +++++++++++++++++++-----
 tests/unit/test_release_workflow_gate.py | 48 ++++++++++++++++++++++++++++++++
 tickets/T-3426/ticket.md                 | 11 ++++++--
 3 files changed, 86 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_test_step_budget_at_least_40_minutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_job_timeout_minutes_exceeds_ubuntu_step_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_step_still_uses_faulthandler_and_sigabrt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 13 error(s), 3961 warning(s), 856 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3426, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py
