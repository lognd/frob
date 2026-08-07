---
id: T-1259
title: 'ledger v2: migration (frob ticket migrate --to v2, golden round-trip, deprecation
  gate, final cutover)'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1253
- T-1254
- T-1255
- T-1256
- T-1257
- T-1258
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- src/frob/gates/**
- docs/modules/tickets.md
- .gitattributes
- tests/fixtures/tickets/**
- tests/test_tickets_migration.py
- design/frob.strata
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SYS100/SYS104 self-audit gate flags migrate_v1_to_v2 as an undeclared public
    interface symbol and tests/test_tickets_migration.py's subprocess/read_text calls
    as undeclared testsuite capability effects (exec/fs.read) -- structural necessity
    for any new public symbol/test file, same shape as the CLI-wiring-files precedent
    (T-0446), not scope creep
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_monofiles_left_in_place_reversible
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_attachment_moved_under_ticket_dir
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_archived_ticket_lands_under_archive_dir
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_draft_id_ticket_migrates_like_any_other
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_idempotent_no_v1_state_is_a_no_op
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent
designated_repro_test: null
acceptance:
- text: "Deliverables (design section 7, this ticket owns ALL of them):\n1. `frob\
    \ ticket migrate --to v2`: one-shot, reversible migrator reading\n   today's `tickets.md`/`tickets-archive.md`\
    \ via existing `_parse_ledger`,\n   writing `tickets/T-####/ticket.md` + `done-report.md`\
    \ + moved\n   attachments -- WITHOUT deleting the monofiles in the same commit.\n\
    2. Golden round-trip test: migrate a fixture ledger to v2, migrate v2\n   back\
    \ to a monofile rendering, assert semantic equality (same id set,\n   field values,\
    \ Done-report text) even if not byte-identical.\n3. A new deprecation-class gate\
    \ (name TBD, e.g. LEDGERV1001) warning on\n   monofile-mode repos once v2 ships,\
    \ mirroring the existing DEPR00x\n   escalation-after-expiry pattern.\n4. Final-cutover\
    \ step (separate commit within this ticket, or an\n   explicitly filed follow-up\
    \ if judged too large): flip the fresh-repo\n   default to v2, delete `_render_ledger`/`splice_ledger`/\n\
    \   `_land_merge.py`/`_land_merge_zones.py`, remove the `.gitattributes`\n   merge-driver\
    \ line."
  evidence:
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_monofiles_left_in_place_reversible
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_attachment_moved_under_ticket_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_archived_ticket_lands_under_archive_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_draft_id_ticket_migrates_like_any_other
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_idempotent_no_v1_state_is_a_no_op
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent
- text: 'Do NOT delete the v1 monofile code path until the golden round-trip test

    is green AND a compatibility-window period has been explicitly recorded

    (a dated note in docs/modules/tickets.md is sufficient evidence, no fixed

    calendar length is prescribed here -- follow the DEPR00x precedent''s own

    expiry-recording convention).'
  evidence:
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_monofiles_left_in_place_reversible
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_attachment_moved_under_ticket_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_archived_ticket_lands_under_archive_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_draft_id_ticket_migrates_like_any_other
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_idempotent_no_v1_state_is_a_no_op
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent
- text: 'GIVEN a fixture monofile ledger covering a done ticket with a Done

    report, a queued ticket with blocked_by, a ticket with attachments, an

    archived ticket, and a draft-id ticket

    WHEN it is migrated to v2 then migrated back to a monofile rendering

    THEN the round-tripped rendering parses to an equal id-set and equal

    per-ticket field values and Done-report text as the original (golden

    round-trip test, T-1136 acceptance[1]''s reversibility requirement).'
  evidence:
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_monofiles_left_in_place_reversible
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_attachment_moved_under_ticket_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_archived_ticket_lands_under_archive_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_draft_id_ticket_migrates_like_any_other
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_idempotent_no_v1_state_is_a_no_op
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent
- text: 'GIVEN a migration mid-way through the compatibility window

    WHEN `frob check` runs against a monofile-mode repo

    THEN it reports a new deprecation-class warning (not yet an error) naming

    the v2 migration path, escalating to error only after an explicitly

    recorded expiry.'
  evidence:
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_monofiles_left_in_place_reversible
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_attachment_moved_under_ticket_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_archived_ticket_lands_under_archive_dir
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_draft_id_ticket_migrates_like_any_other
  - tests/test_tickets_migration.py::TestMigrateV1ToV2::test_idempotent_no_v1_state_is_a_no_op
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent
acceptance_amendments:
- op: remove
  index: 5
  old_text: 'GIVEN the final cutover has landed

    WHEN a real land runs

    THEN it performs no monofile splice (T-1136 acceptance[1]), two agents

    landing disjoint tickets produce no ledger merge conflict, and the

    TICK002/TICK006 draft-death classes described in the epic are

    structurally impossible (draft directories are disjoint git objects,

    verified by a regression test reproducing the T-1115/T-1126/T-1127/

    T-1128 draft-death shape against v2 and asserting no draft is lost).'
  new_text: null
  reason: 'Final cutover (design section 7 deliverable 4) deliberately deferred: a
    live cutover of this repo''s own ledger mid multi-agent drive risks every in-flight
    worktree, and the dispatch explicitly instructed NOT to do it this session. Filed
    T-draft-6204065f (final cutover: flip fresh-repo default, delete v1 splice machinery,
    the T-1115/T-1126/T-1127/T-1128 draft-death regression test) to carry this acceptance
    criterion forward once its stated preconditions (a real quiet-window migrate +
    an observed deprecation-window interval) hold.'
  actor: logan
  at: '2026-08-03'
- op: remove
  index: 0
  old_text: 'The migration child ticket, per T-1136''s epic body ("migration is a

    separate child... with golden round-trip tests") and design doc section

    7. Blocked by every design-implementing child (lock model, store

    backend, renumber, archive, doable/index, land merge-story retirement) --

    migration only makes sense once v2 is a fully working alternate mode.'
  new_text: null
  reason: Not a testable GIVEN/WHEN/THEN criterion -- background rationale explaining
    why this ticket is blocked_by the design-implementing children (T-1253..T-1258),
    duplicated verbatim from T-1136's epic body into the ticket's Description/blocked_by
    field already. No evidence id can bind to a why-this-exists statement; removing
    it here since it carries no acceptance content distinct from the ticket's own
    blocked_by/scope fields.
  actor: logan
  at: '2026-08-03'
threat: null
component: null
---
The migration child ticket, per T-1136's epic body ("migration is a
separate child... with golden round-trip tests") and design doc section
7. Blocked by every design-implementing child (lock model, store
backend, renumber, archive, doable/index, land merge-story retirement) --
migration only makes sense once v2 is a fully working alternate mode.

Deliverables (design section 7, this ticket owns ALL of them):
1. `frob ticket migrate --to v2`: one-shot, reversible migrator reading
   today's `tickets.md`/`tickets-archive.md` via existing `_parse_ledger`,
   writing `tickets/T-####/ticket.md` + `done-report.md` + moved
   attachments -- WITHOUT deleting the monofiles in the same commit.
2. Golden round-trip test: migrate a fixture ledger to v2, migrate v2
   back to a monofile rendering, assert semantic equality (same id set,
   field values, Done-report text) even if not byte-identical.
3. A new deprecation-class gate (name TBD, e.g. LEDGERV1001) warning on
   monofile-mode repos once v2 ships, mirroring the existing DEPR00x
   escalation-after-expiry pattern.
4. Final-cutover step (separate commit within this ticket, or an
   explicitly filed follow-up if judged too large): flip the fresh-repo
   default to v2, delete `_render_ledger`/`splice_ledger`/
   `_land_merge.py`/`_land_merge_zones.py`, remove the `.gitattributes`
   merge-driver line.

Do NOT delete the v1 monofile code path until the golden round-trip test
is green AND a compatibility-window period has been explicitly recorded
(a dated note in docs/modules/tickets.md is sufficient evidence, no fixed
calendar length is prescribed here -- follow the DEPR00x precedent's own
expiry-recording convention).

GIVEN a fixture monofile ledger covering a done ticket with a Done
report, a queued ticket with blocked_by, a ticket with attachments, an
archived ticket, and a draft-id ticket
WHEN it is migrated to v2 then migrated back to a monofile rendering
THEN the round-tripped rendering parses to an equal id-set and equal
per-ticket field values and Done-report text as the original (golden
round-trip test, T-1136 acceptance[1]'s reversibility requirement).

GIVEN a migration mid-way through the compatibility window
WHEN `frob check` runs against a monofile-mode repo
THEN it reports a new deprecation-class warning (not yet an error) naming
the v2 migration path, escalating to error only after an explicitly
recorded expiry.

GIVEN the final cutover has landed
WHEN a real land runs
THEN it performs no monofile splice (T-1136 acceptance[1]), two agents
landing disjoint tickets produce no ledger merge conflict, and the
TICK002/TICK006 draft-death classes described in the epic are
structurally impossible (draft directories are disjoint git objects,
verified by a regression test reproducing the T-1115/T-1126/T-1127/
T-1128 draft-death shape against v2 and asserting no draft is lost).