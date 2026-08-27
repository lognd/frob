## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_dispose_to_existing_duplicate_or_none

Fix: mirrored the existing DuplicateTicket branch for the DuplicateFinding
case (T-2760's `(rule, file)` overlap refusal). When `new_ticket` refuses
a sweep-filed regression ticket with DuplicateFinding, resolve the
declaring ticket via `_find_finding_duplicate` and dispose the unfiled
pairs to it, exactly as the DuplicateTicket branch already does for
title+scope duplicates. Any other failure (including an unresolvable
duplicate) still logs ERROR and returns None, unchanged.

Both fixture directions:
- must-work: test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping
  files an open ticket under a DIFFERENT title that already declares
  ("RULE1", "a.py"), then calls _file_regression_ticket with the same
  pair -- asserts it disposes to the declaring ticket's id (not None) and
  quarantine clears.
- must-still-refuse: test_unrelated_duplicate_finding_in_a_different_file_still_refuses
  files an open ticket declaring an unrelated pair ("RULE2", "b.py"),
  then calls _file_regression_ticket with ("RULE1", "a.py") -- asserts a
  NEW ticket is filed (never mistakes the unrelated ticket for the
  owner).

Evidence: tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping, tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unrelated_duplicate_finding_in_a_different_file_still_refuses -- both PASS (pytest -q, 2/2 collected/passed); the existing 10 TestFileRegressionTicket tests also re-run clean (12/12).

Filed: none -- the H4 fix is a one-function change scoped exactly to
_dispose_to_existing_duplicate_or_none; no out-of-scope work found.

Gates: `frob check --only gates-fast --ticket T-3051` clean of new
findings introduced by this change (gate:SCOPE, gate:PRE, gate:COV
COV002 all clear after scoping tests/unit/test_rapid_sweep.py and adding
frob:ticket/frob:tests edges). Remaining gate:COV/DOC/DRIFT/REF/REG/
TICK/WAIVE failures are pre-existing repo-wide debt unrelated to this
diff (verified via `git grep _rapid_sweep` over the gate output -- only
this ticket's own touched lines appear, and those are either clean or
carry pre-existing waivers this change did not touch).

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  40 ++++++++-
 tests/unit/test_rapid_sweep.py             | 127 +++++++++++++++++++++++++++++
 tickets/T-3051/ticket.md                   |  25 +++++-
 3 files changed, 187 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unrelated_duplicate_finding_in_a_different_file_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 62 error(s), 794 warning(s), 860 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3051-series/src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3051-series/src/frob/narrative/_cli.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3051-series/src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
