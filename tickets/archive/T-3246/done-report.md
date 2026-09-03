## Done report

Changed:
tests/conftest.py::pytest_sessionfinish
tests/conftest.py::pytest_internalerror
tests/conftest.py::pytest_configure
tests/conftest.py::_COMPLETED_EXIT_STATUSES
tests/conftest.py::_EXIT_STATUS_LABELS
tests/conftest.py::_last_internal_error
tests/unit/test_conftest_suite_result_status.py (new file)

Evidence:
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_labels_did_not_complete_runs
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_completed_run_format_is_unchanged
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_marks_failing_set_incomplete_on_abort
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_completed_run_never_marked_incomplete
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_names_internalerror_cause
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_configure_resets_stale_internal_error
tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_prints_greppable_line_at_any_verbosity (unchanged, still pins exitstatus=1 format)

Filed: T-3252 (consolidate the duplicated _load_conftest test helper once T-3244 releases its scope lease on tests/unit/test_conftest_stackdump.py)

Gates: frob check --ticket T-3246 clean except:
  - DUP001/REL001 at tests/unit/test_conftest_suite_result_status.py::_load_conftest -- tracked as frob:debt (not waived) bound to open ticket T-3252, since test_conftest_stackdump.py (home of the pre-existing near-duplicate) was under a live T-3244 scope lease and could not be edited to share a helper
  - SEC110 at tests/conftest.py:590,602 -- waived, pre-existing dispatch-context env-var reads (T-0574), same shape as .claude/hooks/_agent_context.py's existing waivers
  - WIRE001 at tests/conftest.py::pytest_internalerror -- waived with follow_up=T-3246, genuinely wired via pytest's hook-discovery protocol (same shape as the file's pre-existing pytest_configure/pytest_sessionfinish hooks)
  - FMT001 (11 sites) -- waived, unwrappable long frob:tests directive lines naming test node ids, same precedent as src/frob/app/_json_guard.py

Design note: the DID-NOT-COMPLETE line preserves the bare `collected=N`/`failed=N` substrings (partial-ness noted as a trailing annotation, not folded into the key) because src/frob/gates/_bug_repro.py::_classify_designated_test_exit regex-matches `\bcollected=0\b` against this exact line to detect a "test does not exist" repro run (T-2025) -- a sibling consumer of this line, checked per the ticket's "check for siblings" instruction. Covered by tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_labels_did_not_complete_runs's explicit assertion on that substring.

Sibling audit (per ticket): grepped the repo for other exit-code/SUITE-RESULT consumers. Only src/frob/gates/_bug_repro.py::_classify_designated_test_exit reads the SUITE-RESULT line (compatibility preserved, see above). No other branch-on-zero/non-zero-only exit-code consumer of this line was found in frob test/land/evidence code.

### Changed
```
 rapid-debt.jsonl                                |   7 +
 tests/conftest.py                               | 135 ++++++++++-
 tests/unit/test_conftest_suite_result_status.py | 289 ++++++++++++++++++++++++
 tickets/T-3246/done-report.md                   |  54 +++++
 tickets/T-3246/ticket.md                        |  11 +-
 5 files changed, 491 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_format_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_marks_failing_set_incomplete_on_abort` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_never_marked_incomplete` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_names_internalerror_cause` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_configure_resets_stale_internal_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 96 error(s), 3901 warning(s), 890 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, DSL001@src/frob/gates/__init__.py, DUP001@tests/unit/test_conftest_suite_result_status.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
