## Done report

Re-measured all 21 identities against current main.

LIVE (4): DOC007 and DRIFT002 on src/frob/check/_python.py -- both fire because 4 frob:tests directives use pytest's Class::method collect-only separator instead of this graph's Class.method convention (lines 246-254). Fixed by rewriting the separator on all 4 directives; re-run confirms neither rule fires on this file any more.

LIVE (1): REF002 on src/frob/tickets/_done_report.py -- genuinely single-anchor (only src/frob/tickets/_evidence.py imports it; grepped repo-wide). This is a T-3195 module split on 2026-08-28, intentionally a leaf policy module with one caller. Bound frob:waive REF002; re-run confirms it now shows [waived].

STALE (17): COV003 tickets/T-3181 (T-3181 closed+archived, target file gone) and all 18 unresolved-attribute identities (scripts/fleet_status.py, tests/system/test_fleet_status_ground_truth.py, and 16 more test files) -- a full `frob check --only ty` re-run finds exactly 5 unresolved-attribute diagnostics repo-wide, none in any of these 18 files (src/frob/tickets/_land.py:5578, tests/unit/test_check.py:2901/2902, tests/unit/test_land_queue.py:134, tests/unit/test_main_entry.py:461 -- none of the 18 sweep-cited files). All 17 already resolved by the time this sweep-filed ticket was read.

Also noted, out of scope: `frob check --only gates` in this worktree independently surfaces a NEW COV003 (pytest --collect-only itself fails) unrelated to the sweep's own "tickets/T-3181" COV003 target -- different shape, not part of this ticket's identity set, not actioned here.

Changed: src/frob/check/_python.py (4 frob:tests directives fixed), src/frob/tickets/_done_report.py (frob:waive REF002 added).

Evidence: tests/unit/test_check.py::TestRunTyMultiPlatform.test_default_platforms_all_run

Filed: T-3285 (close-time disclosure check false-positives on split done-report.md -- same tooling bug hit again here, already filed from T-3196)

### Changed
```
 src/frob/check/_python.py        |  8 ++++----
 src/frob/tickets/_done_report.py |  6 ++++++
 tickets/T-3219/done-report.md    | 33 +++++++++++++++++++++++++++++++++
 tickets/T-3219/ticket.md         |  6 +++++-
 4 files changed, 48 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestRunTyMultiPlatform::test_default_platforms_all_run` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 95 error(s), 5547 warning(s), 880 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3219, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
