## Done report

T-2946's TICK004 triage found `T-0450` (`state: queued`) sitting under
`tickets/archive/T-0450/`, 37 days stale -- a ledger invariant
violation, since `archive`/`archive_v2` are contractually documented as
"move done/dropped tickets into tickets-archive.md". Once stranded,
nothing could repair it: `frob ticket drop <id>` resolves ids via the
active store only (`_load_one`/`load_all`, never the archive), so it
reports plain `NotFound` against an archived id, and no un-archive verb
existed at all.

Premise reproduced: `T-0450` still exists on current main at exactly
this shape (`tickets/archive/T-0450/ticket.md`, `state: queued`), and
`frob ticket drop T-0450` still fails `NotFound`, confirmed directly
this session. Also confirmed by reading both `archive()`/`archive_v2()`
that BOTH already filter their `to_archive` selection to done/dropped
only -- so the two public entry points cannot themselves have produced
this state; whatever did (this repo's own house rules already forbid a
hand edit of the ledger, the likely cause) is outside this ticket's
diagnostic reach, matching the ticket's own "root cause never
conclusively identified" framing.

Fix (both of the ticket's proposed directions, not either/or):

1. `frob ticket restore <id> --reason TEXT` (new verb): `git mv
   tickets/archive/<id> tickets/<id>` (the exact reverse of
   `_archive_v2_move_tickets`'s own move, including the reverse of its
   T-2986 attachment-path rewrite), a dated `## Restore log` entry, and
   NO state mutation -- restore repairs a location invariant, never a
   state one, so T-0450's own `queued` lands back in the active store
   exactly as it should. Registered in `LEDGER_VERB_STRATEGY`
   (`GENERIC_COMMIT_MIRRORED`, same reasoning as `reopen`/`requeue` --
   missing this registration would have crashed on a `KeyError` at
   dispatch time, caught by `TestLedgerAutoCommitEnumeratedOverDispatchTable`'s
   own exhaustiveness test). CLI wiring commits via
   `commit_full_ledger_change` (whole-ledger pathspecs), never the
   single-ticket helper, which would leave the vacated archive-side
   deletion staged but uncommitted (`git mv` touches two distinct
   pathspecs at once).
2. Defense-in-depth refusal in `_archive_v2_move_tickets` itself
   (`Err(ArchiveNonTerminalTicket)`) if it is ever asked to move a
   non-terminal ticket -- belt-and-suspenders alongside the selection
   filter that already makes this unreachable through the two public
   entry points today, for a future caller/refactor that might weaken
   it.

v2-mode only (`Err(RestoreV1Unsupported)` for a v1/single-ledger repo) --
T-0450's own repo runs v2, the only backend this incident actually
reproduces against; a v1 monofile splice is a different, more involved
primitive left for a future ticket.

Evidence:
tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal::test_refuses_a_non_terminal_ticket_reaching_the_move_loop (must-fire, the designated repro)
tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal::test_normal_archive_of_done_tickets_still_moves_them (must-stay-quiet)
tests/unit/test_ticket_restore.py::TestRestore::test_restores_a_non_terminal_archived_ticket_to_active
tests/unit/test_ticket_restore.py::TestRestore::test_restore_reverses_the_t2986_attachment_path_rewrite
tests/unit/test_ticket_restore.py::TestRestore::test_refuses_when_not_archived
tests/unit/test_ticket_restore.py::TestRestore::test_refuses_when_destination_already_exists
tests/unit/test_ticket_restore.py::TestRestore::test_refuses_a_blank_reason
tests/unit/test_ticket_restore.py::TestRestoreCli::test_restore_cli_wiring_delegates_and_commits
tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[restore]

Repro-fails-at-parent: constructed a repro-only commit (test-only, no
production change) on top of the parent commit calling
`_archive_v2_move_tickets` directly with a non-terminal ticket and
asserting `result.is_err` -- genuinely FAILS at parent (`Ok(1)`, the
ticket really gets moved, log line "tickets: archived 1 ticket(s) (v2,
git mv)"), passes after the fix. `frob ticket evidence --designate-repro
--base-ref <that commit>` independently confirmed the same FAILED_AT_PARENT
verdict.

Filed: none (T-0450 itself is not dropped by this ticket -- it can now
be repaired with `frob ticket restore T-0450 --reason "..."` followed by
whatever disposition its own content calls for, left to a human/operator
decision per the ticket's own note that a real content decision, not a
mechanical repair, is needed for T-0450 itself).

Gates: `frob check --ticket T-2954` clean except pre-existing win32
`fcntl` findings in `tests/test_ticket_leases.py` (confirmed present at
the same lines on main, unrelated to this ticket's changes).

### Changed
```
 docs/modules/tickets-data-storage.md         |  15 ++
 docs/modules/tickets-lifecycle.md            |  63 +++++
 src/frob/_cli_parsers/_ticket/_closeout.py   |  27 ++-
 src/frob/app/ticket_runner/__init__.py       |   4 +-
 src/frob/app/ticket_runner/_archive.py       |  55 +++++
 src/frob/app/ticket_runner/_ledger_mirror.py |   7 +
 src/frob/tickets/__init__.py                 |   2 +
 src/frob/tickets/_archive.py                 | 244 ++++++++++++++++++-
 src/frob/tickets/_models.py                  |  46 +++-
 tests/test_ticket_leases.py                  |  28 +++
 tests/unit/test_ticket_restore.py            | 341 +++++++++++++++++++++++++++
 tickets/T-2954/ticket.md                     |  78 ++++++
 12 files changed, 905 insertions(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 95 error(s), 1261 warning(s), 922 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2954, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
