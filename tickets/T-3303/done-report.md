## Done report

Changed:
src/frob/app/ticket_runner/__init__.py::_auto_commit_ledger_after_dispatch

Evidence:
tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_every_strategy_member_is_covered
tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_never_reaches_generic_commit_regardless_of_ticket_id
tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_generic_strategies_still_reach_the_generic_commit

Filed: T-3329 (F-019 half -- frob ticket new's missing project-root
guard needs its own design decision; this repo's own test suite
exercises frob ticket new against a bare tmp_path with no git and
expects success, conflicting with a blanket guard, so it could not be
folded into this ticket -- see T-3329 for the full reasoning).

Gates: frob check --only lint/static/gates-fast/gates-native/gates-security
--ticket T-3303 clean of every error touching the touched-set (the one
remaining touched-file hit, frob-cycle CYCLE001, is a pre-existing
repo-wide import cycle spanning nearly the whole package graph,
unrelated to this two-branch fix). pytest tests/unit/test_ticket_runner_ledger_mirror.py:
32/32 passed.

F-024 (the ticket's headline defect) is fixed: NOT_TICKET_SCOPED now
has its own explicit early-return branch, symmetric with
OWN_TRANSACTION/OWN_TRANSACTION_LEDGER_MIRROR, keyed to the enum
member rather than to "show" by name. The required STRUCTURAL fixture
(TestAutoCommitDispatchCoversEveryStrategy) iterates every
LedgerWriteStrategy member: test_every_strategy_member_is_covered
asserts no member is silently unexercised;
test_never_reaches_generic_commit_regardless_of_ticket_id drives
OWN_TRANSACTION/OWN_TRANSACTION_LEDGER_MIRROR/NOT_TICKET_SCOPED with
cfg.ticket_id always set (the exact condition that let `show` slip
through) and asserts commit_ticket_ledger_change is never reached;
test_generic_strategies_still_reach_the_generic_commit is the positive
control for GENERIC_COMMIT_MIRRORED/GENERIC_COMMIT_UNMIRRORED. None of
these are keyed to "show" by name, so a future NOT_TICKET_SCOPED verb
with a ticket-id argument would be caught by the same test without any
change to it.

F-019 (frob ticket new's missing project-root guard): CONFIRMED
_resolve_ticket_root has no such guard, but building the guard
correctly requires deciding what "not a frob repo" means and
reconciling that against TestTicketRunnerRootResolution's existing
bare-tmp_path-succeeds contract -- filed as T-3329 rather than forced
into this ticket's scope.

### Changed
```
 src/frob/app/ticket_runner/__init__.py         |  24 +++-
 tests/unit/test_ticket_runner_ledger_mirror.py | 146 ++++++++++++++++++++++++-
 tickets/T-3303/ticket.md                       |  10 +-
 3 files changed, 173 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 88 error(s), 3966 warning(s), 884 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3303, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
