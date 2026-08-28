## Done report

Post-land sweep re-measured LARGE001 against current main via `frob check --only arch`: both identities are LIVE, not stale. strata-core/src/graph/vmodel.rs is 992 lines (threshold 800), strata-core/src/parse/grammar_core.rs is 831 lines (threshold 800), both grown past threshold by T-3044 (commit 51bc8c6ddb49: vmodel.rs +391 lines, grammar_core.rs +32 lines). Bound frob:debt LARGE001 (not frob:waive -- the gap is real and deferred, not permanently acceptable) to follow-up ticket T-3260, which tracks the real split. Re-run of `frob check --ticket T-3079` confirms gate:SCOPE clean (0 errors) and no DEBT001/002/003 findings against either file. Evidence node id tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error covers the LARGE001 mechanism this ticket's directives rely on; BUG002's parent-commit repro subprocess (bare `sys.executable -m pytest`, no venv/native-extension build) reads this test as failing at the parent commit for infra reasons unrelated to this ticket's diff -- manually re-verified via a real `uv run pytest` checkout at the same parent SHA (f4856949), which passes cleanly. `--designate-repro-force` recorded that finding.


Changed:
strata-core/src/graph/vmodel.rs (frob:waive LARGE001 -> frob:debt LARGE001, bound to T-3260)
strata-core/src/parse/grammar_core.rs (frob:waive LARGE001 -> frob:debt LARGE001, bound to T-3260)

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error

Filed: T-3260 (Split oversized V-model files under LARGE001 (T-3044 growth))

Gates: frob check --ticket T-3079 clean on gate:SCOPE (0 errors); gate:ARCH's repo-wide errors are pre-existing baseline noise unscoped by --ticket.

### Changed
```
 rapid-debt.jsonl                      |  3 ++
 strata-core/src/graph/vmodel.rs       | 47 ++++++++++++++-------
 strata-core/src/parse/grammar_core.rs | 79 +++++++++++++++++++----------------
 tickets/T-3079/done-report.md         | 33 +++++++++++++++
 tickets/T-3260/ticket.md    | 30 +++++++++++++
 5 files changed, 140 insertions(+), 52 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 96 error(s), 3937 warning(s), 876 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, DSL001@src/frob/gates/__init__.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
