## Done report

`_pending_draft_ids_after_close` (the `frob ticket close` draft
auto-promote sweep, T-2738) swept EVERY still-open `T-draft-*` id in the
whole fleet-wide merged queue (`load_queue(root)`), with no check at all
for which ticket actually created a given draft. Live-hit: T-2872's
close auto-promoted `T-draft-90b2bcf5`, a draft filed by a completely
unrelated ticket's own COV007 work; main independently promoted the SAME
draft to a different id around the same time (its rightful owner's own
close/land), and the two renames collided as a rename/rename git
conflict on `frob ticket land T-2872`.

Premise reproduced: confirmed `_pending_draft_ids_after_close`'s
implementation on current main filters only by draft-id-shape and
non-terminal state, with zero ownership/provenance check -- exactly the
defect the ticket describes. Also confirmed (per the ticket's own
"Root structural gap" analysis) that no field on `Ticket` records which
ticket filed a given draft.

Fix: rather than adding a new schema field (the ticket's own "Scope
note" explicitly defers that to separate schema/migration work, filed
here as T-2880), this reuses TICK006's own hardened, already-tested
"Filed: <id>" claim parser (`_tick006_phantom_ids`/
`_tick006_done_report_text`, `frob.gates._tickets_gate`) to scope the
sweep to drafts the CLOSING TICKET'S OWN Done report affirmatively
claims to have filed -- the exact grammar this module's own tests
already used as their fixture convention. No new parsing surface, no
schema change, and it directly restores T-2738's stated intent ("the
draft is promoted ... [drafts] the closing ticket FILED", never anyone
else's).

Evidence:
tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_never_sweeps_a_draft_it_did_not_claim (must-stay-quiet: T-2872's exact incident shape -- an unrelated ticket's pending draft survives close untouched)
tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_ignores_an_already_dropped_draft
tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged
tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted

Repro-fails-at-parent: `test_close_never_sweeps_a_draft_it_did_not_claim`
genuinely FAILS at the parent commit -- confirmed by reverting only
`_close_cmd.py` to the parent's content and re-running that one test id,
which failed: the unrelated draft got swept and finalized to `T-0901`
(log line: "ticket close: T-0900: promoted pending draft
T-draft-<hex> -> T-0901").

Filed: T-3226 -- add a real filing-provenance field to the
ticket schema (which ticket created a given `T-draft-*` id), so
`_pending_draft_ids_after_close` (and any future ownership-scoped draft
query) can filter on real data instead of Done-report prose-parsing;
the "Filed:" claim parser this fix reuses is a good-enough interim
signal but is still text-matching, not a structural guarantee.

Gates: `frob check --ticket T-2878` clean on both touched files (DUP001
waived on the new must-stay-quiet test with a stated reason -- a
genuinely distinct guard from the existing dropped-draft test, sharing
fixture shape by necessity).

### Changed
```
 src/frob/app/ticket_runner/_close_cmd.py | 60 +++++++++++++++++++++++++++-----
 tests/unit/test_close_promote_drafts.py  | 56 ++++++++++++++++++++++++++++-
 tickets/T-3226/ticket.md       | 31 +++++++++++++++++
 3 files changed, 138 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 92 error(s), 748 warning(s), 875 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2878, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
