---
id: T-2954
title: frob ticket archive can strand a non-terminal ticket with no restore path (T-0450)
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner/*archive*
- src/frob/_cli_parsers/_ops.py
- src/frob/tickets/_archive.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- tests/unit/test_ticket_restore.py
- docs/modules/tickets-lifecycle.md
- src/frob/app/ticket_runner/_ledger_mirror.py
- tests/test_ticket_leases.py
- src/frob/tickets/_models.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/*
  reason: 'narrow: the restore/drop-archived CLI wiring belongs with the other ticket
    subcommands, not the whole parsers package'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: 'narrow: the restore/drop-archived CLI wiring belongs with the other ticket
    subcommands, not the whole parsers package'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/_archive.py
  reason: 'the real files: _ops.py in the original scope does not register ticket
    verbs at all (that is the ''frob ops'' group); the actual CLI wiring for archive/drop/reopen
    lives in _cli_parsers/_ticket/_closeout.py + app/ticket_runner/__init__.py''s
    dispatch table, and archive''s own core primitive lives in tickets/_archive.py,
    not _store.py'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'the real files: _ops.py in the original scope does not register ticket
    verbs at all (that is the ''frob ops'' group); the actual CLI wiring for archive/drop/reopen
    lives in _cli_parsers/_ticket/_closeout.py + app/ticket_runner/__init__.py''s
    dispatch table, and archive''s own core primitive lives in tickets/_archive.py,
    not _store.py'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'the real files: _ops.py in the original scope does not register ticket
    verbs at all (that is the ''frob ops'' group); the actual CLI wiring for archive/drop/reopen
    lives in _cli_parsers/_ticket/_closeout.py + app/ticket_runner/__init__.py''s
    dispatch table, and archive''s own core primitive lives in tickets/_archive.py,
    not _store.py'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_ticket_restore.py
  reason: 'the real files: _ops.py in the original scope does not register ticket
    verbs at all (that is the ''frob ops'' group); the actual CLI wiring for archive/drop/reopen
    lives in _cli_parsers/_ticket/_closeout.py + app/ticket_runner/__init__.py''s
    dispatch table, and archive''s own core primitive lives in tickets/_archive.py,
    not _store.py'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: restore command needs a doc anchor; tickets-lifecycle.md already documents
    archive/reopen/drop in the same place
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/ticket_runner/_ledger_mirror.py
  reason: restore must be classified in LEDGER_VERB_STRATEGY (T-2603) or ledger_write_strategy_for
    raises a loud KeyError on dispatch; restore needs GENERIC_COMMIT_MIRRORED, same
    reasoning as reopen/requeue
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_leases.py
  reason: TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
    enumerates every dispatch verb by hand; restore must be filed into it
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_models.py
  reason: the new TicketError members (RestoreReasonMissing etc, ArchiveNonTerminalTicket)
    live in _models.py; AFFECT001 requires touching the error-types doc section that
    closure-covers TicketError
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: the new TicketError members (RestoreReasonMissing etc, ArchiveNonTerminalTicket)
    live in _models.py; AFFECT001 requires touching the error-types doc section that
    closure-covers TicketError
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: set
  reason: reword to avoid DOC006 false-hit on a proposed, not-yet-existing subcommand
    name
  actor: logan
  at: '2026-08-26'
  old_length: 1722
  new_length: 1743
evidence:
- tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal::test_refuses_a_non_terminal_ticket_reaching_the_move_loop
- tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal::test_normal_archive_of_done_tickets_still_moves_them
- tests/unit/test_ticket_restore.py::TestRestore::test_restores_a_non_terminal_archived_ticket_to_active
- tests/unit/test_ticket_restore.py::TestRestore::test_restore_reverses_the_t2986_attachment_path_rewrite
- tests/unit/test_ticket_restore.py::TestRestore::test_refuses_when_not_archived
- tests/unit/test_ticket_restore.py::TestRestore::test_refuses_when_destination_already_exists
- tests/unit/test_ticket_restore.py::TestRestore::test_refuses_a_blank_reason
- tests/unit/test_ticket_restore.py::TestRestoreCli::test_restore_cli_wiring_delegates_and_commits
- tests/unit/test_ticket_restore.py::TestRestoreCli::test_restore_exits_when_ticket_id_missing
- tests/unit/test_ticket_restore.py::TestRestoreCli::test_restore_exits_when_reason_missing
- tests/unit/test_ticket_restore.py::TestRestoreCli::test_restore_reason_flag_is_required_by_the_real_parser
designated_repro_test: tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal::test_refuses_a_non_terminal_ticket_reaching_the_move_loop
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2946 triage of TICK004 found T-0450 living under tickets/archive/T-0450/
(state: queued, priority: medium, created 2026-07-20 -- 37 days old) with no
body beyond its title. `frob ticket archive`'s own contract is "move
done/dropped tickets into tickets-archive.md" -- a queued ticket under
tickets/archive/ is therefore a ledger invariant violation: it was moved out
of the active queue without ever reaching a terminal state.

No CLI primitive exists to repair this safely: `frob ticket drop <id>` looks
up the active ledger only (confirmed: "NotFound: No ticket with that id"
against T-0450), and this repo has no un-archive/restore command to move a
ticket's directory back into the active tickets/ tree. Hand-editing the
ticket directory or frontmatter directly is against this repo's own
standing rule (never hand-edit the ledger).

Two things worth fixing, either or both:
1. A new restore-style subcommand for exactly this repair case (proposed
   shape: id in, ticket's directory moved back into tickets/ and its state
   set back to queued's prior value, git-tracked like every other ticket
   mutation the same way archive/drop/set-parent already are).
2. The archive write path should refuse (or at minimum warn loudly) if it
   is ever asked to move a non-terminal ticket -- whatever produced this
   state should not be able to reproduce it silently again.

T-0450 itself should be dropped once (1) exists (restore it to active
first so drop can find it, or extend drop/evidence-style commands to
accept an archived-ticket flag the way ticket evidence already accepts
one for archived ids) -- left queued-in-archive in the meantime, since
neither this repo's tooling nor its house rules give a safe way to
correct it right now.