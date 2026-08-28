## Done report

Changed:
src/frob/ci_report.py::TestFailure
src/frob/ci_report.py::FailureCluster
src/frob/ci_report.py::JobReport
src/frob/ci_report.py::RunReport
src/frob/ci_report.py::parse_pytest_log
src/frob/ci_report.py::build_job_report
src/frob/ci_report.py::build_run_report

Evidence: 11 pytest node ids in tests/test_ci_report.py (see evidence list),
all observed collected and passing via pytest tests/test_ci_report.py -q
(SUITE-RESULT: exitstatus=0 collected=11 failed=0).

Filed: none

Gates: frob check --only coverage --ticket T-2984 (repo-wide gate:COV/DRIFT
counts pre-existing, zero hits naming ci_report.py or test_ci_report.py);
frob fmt --check shows only pre-existing Rust drift, no Python files.

### Changed
```
 docs/modules/ci_report.md |  89 +++++++++++++
 src/frob/ci_report.py     | 321 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_ci_report.py   | 225 ++++++++++++++++++++++++++++++++
 tickets/T-2984/ticket.md  |  40 +++++-
 4 files changed, 674 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_report.py::TestParsePytestLog::test_parses_named_failures` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestParsePytestLog::test_clean_run_is_no_failures` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestParsePytestLog::test_no_result_line_is_not_recoverable` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestParsePytestLog::test_truncated_with_no_evidence_is_not_recoverable` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestParsePytestLog::test_never_reports_clean_for_a_truncated_run_with_apparent_result` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestBuildJobReport::test_clean_job` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestBuildJobReport::test_failures_clustered` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestBuildJobReport::test_empty_log_propagates_gherror` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestBuildRunReport::test_all_jobs_reported` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestBuildRunReport::test_one_job_log_failure_degrades_not_aborts` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::test_test_failure_model_is_frozen` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 48 error(s), 490 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2990/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/gh-report/src/frob/ci_report.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2984, REF002@docs/modules/ci_report.md, REF002@docs/modules/ghio.md, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, WIRE001@src/frob/ci_report.py
