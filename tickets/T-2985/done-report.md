## Done report

Changed:
src/frob/ci_validity.py::ValidityError
src/frob/ci_validity.py::Validity
src/frob/ci_validity.py::TestValidity
src/frob/ci_validity.py::classify_test
src/frob/ci_validity.py::validity_for_run_head_sha
src/frob/ci_validity.py::JobValidity
src/frob/ci_validity.py::job_validity
src/frob/ci_validity.py::RunValidity
src/frob/ci_validity.py::run_validity

Evidence: 9 pytest node ids in tests/test_ci_validity.py (see evidence
list), observed collected and passing via
pytest tests/test_ci_validity.py -q (SUITE-RESULT: exitstatus=0
collected=9 failed=0). Includes both required classifier directions:
test_stale_when_reached_by_a_touched_symbol / test_stale_when_test_itself_
touched (must-classify-STALE) and test_still_valid_when_nothing_relevant_
changed (must-classify-VALID), plus test_unknown_when_closure_truncated
proving a genuine affects()-truncation reports UNKNOWN, never a false
STILL_VALID (with a same-graph unbounded sanity check reaching STALE).

Filed: none

Gates: frob check --only coverage --ticket T-2985 -- repo-wide gate:COV/
DRIFT counts unchanged from the pre-existing baseline (12/21 errors,
identical to the T-2984 land's own measurement), zero hits naming
ci_validity.py or test_ci_validity.py.

### Changed
```
 docs/modules/ci_validity.md   | 108 ++++++++++++++
 src/frob/ci_validity.py       | 340 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_ci_validity.py     | 252 +++++++++++++++++++++++++++++++
 tickets/T-2985/done-report.md |  46 ++++++
 tickets/T-2985/ticket.md      |  42 +++++-
 5 files changed, 787 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_validity.py::TestClassifyTest::test_still_valid_when_nothing_relevant_changed` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestClassifyTest::test_stale_when_reached_by_a_touched_symbol` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestClassifyTest::test_stale_when_test_itself_touched` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestClassifyTest::test_unknown_when_symbol_unresolvable` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestClassifyTest::test_unknown_when_closure_truncated` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestValidityForRunHeadSha::test_diff_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestValidityForRunHeadSha::test_classifies_every_failing_node` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestJobAndRunValidity::test_job_validity_covers_named_failures` (pytest node id, verified passing when recorded)
- `tests/test_ci_validity.py::TestJobAndRunValidity::test_run_validity_covers_every_job` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 60 error(s), 496 warning(s), 854 waived
- error-findings: ARCH001@src/frob/ci_validity.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2990/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DUP001@tests/test_ci_validity.py, E501@/home/logan/projects/frob/.claude/worktrees/gh-report/src/frob/ci_validity.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2985, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK011@tickets.md, WIRE001@src/frob/ci_validity.py
