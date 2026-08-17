---
id: T-2254
title: 'T-2226''s attachment backfill has no CLI entry point: the repair is unreachable
  and 2 COV004 findings remain, now that T-2239 removed the CRLF blocker'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_draft_finalize.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_attach_backfill.py
- tests/unit/test_draft_finalize_attachments.py
- tests/unit/test_app_runners_batch7.py
- tickets/T-2195/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_attach_backfill.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_draft_finalize_attachments.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'T-2254''s own scope note: CLI wiring for the attachment backfill needs
    the T-2217 dispose-flag precedent''s three files (cli parser, AppConfig field,
    _config_external registration); src/frob/app/ticket_runner/_lifecycle.py is under
    T-2220''s live cross-worktree lease, so the dispatch decision and backfill runner
    are split into a NEW sibling module (_attach_backfill.py) wired via __init__.py''s
    dispatch table instead, leaving _lifecycle.py''s existing _attach untouched; tests/unit/test_app_runners_batch7.py
    owns the existing TestTicketAttach/TestTicketReconcileCli CLI-dispatch smoke tests
    this change''s new tests belong beside'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tickets/T-2195/ticket.md
  reason: 'backfill_stale_draft_attachment_paths --apply (acceptance [2]) writes the
    repaired path: field directly into tickets/T-2195/ticket.md -- the ledger record
    this ticket''s own acceptance criteria requires be corrected'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_apply_writes_and_reports
- tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_dry_run_does_not_write
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_dry_run_reports_without_writing
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_reports_unresolvable_rather_than_guessing
designated_repro_test: tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_apply_writes_and_reports
acceptance:
- text: 'The backfill is invocable from the frob CLI (fails today: four in-module
    references, no parser or runner)'
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_apply_writes_and_reports
- text: Running it repairs the two T-draft-0bd874ac attachment paths on T-2195; unscoped
    frob check --only coverage then reports 0 COV004 (currently 2)
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
- text: Attachment FILES are byte-identical afterwards, verified against the recorded
    sha256; only the ledger path field changes
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
- text: 'MUST-STILL-PASS: a correctly-recorded attachment is untouched, and an unresolvable
    draft id is reported not guessed (T-2226''s existing tests)'
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_reports_unresolvable_rather_than_guessing
- text: A dry-run/report-only mode exists, or an explicit reason is given for its
    absence
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_dry_run_does_not_write
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_dry_run_reports_without_writing
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b8fab3e6e8bb80f3467587dbd37c4b52cba1a851
---
# T-2226's attachment backfill has no CLI entry point, so the repair it enables can only be run from Python -- and two COV004 findings still sit unrepaired

## Measured evidence (2026-08-16)

T-2226 landed `backfill_stale_draft_attachment_paths` + `AttachmentBackfillReport`
in `src/frob/tickets/_draft_finalize.py`. It works. It has never run against
the real ledger, and an operator cannot invoke it:

    $ git grep -n "backfill_stale_draft_attachment_paths" -- src/frob/
    src/frob/tickets/_draft_finalize.py:135   (docstring)
    src/frob/tickets/_draft_finalize.py:152   (def)
    src/frob/tickets/_draft_finalize.py:203   (helper docstring)
    src/frob/tickets/_draft_finalize.py:223   (log line)

Four hits, all inside the defining module. No CLI parser, no runner, no caller.

**The blocker that made it a no-op is now gone.** T-2226 repaired 0 records
because the shared sha-reverify guard correctly refused: the on-disk bytes had
been CRLF-converted and no longer hashed to the recorded value. T-2239
(`bcc3f9858269`) fixed the `.gitattributes` glob, and after renormalising the
working tree the COV004 count dropped 4 -> 2 (verified via
`frob check --only coverage --json`). The two survivors are exactly the
draft-path records this backfill exists to fix:

    tickets/T-2195/attachments/01-...md   ledger path: T-draft-0bd874ac/attachments/01-...
    tickets/T-2195/attachments/02-...md   ledger path: T-draft-0bd874ac/attachments/02-...

Their bytes now match their recorded sha256, so the guard will permit
relocation. Nothing stands between these two findings and repair except the
absence of a way to invoke the function.

## Do NOT fix it this way

- **Do NOT run the repair from a one-off script or a `python -c` in the shared
  root.** The capability must be reachable the same way every other ledger
  operation is, or the next person hits this identical wall. A script also
  dirties the root and DirtyMain-blocks the fleet.
- **Do NOT weaken or bypass the sha-reverify guard.** It is the only thing that
  noticed the CRLF corruption in the first place, and it is why T-2226
  correctly repaired nothing rather than relocating corrupt records.
- **Do NOT hand-edit `tickets.md` or any `ticket.md` to correct the two paths.**
  Hand-editing the ledger has taken every gate in this repo down once.
- **Do NOT delete the attachments to clear the findings.** Those files carry
  T-2195's cross-file-resolution analysis -- silencing a gate by destroying the
  evidence it points at is the worst available outcome.
- **Do NOT invent a new verb surface.** `frob ticket` already has the relevant
  neighbours (`promote`, `attach`, `migrate`, `reconcile`). Fit the existing
  vocabulary; state which you chose and why.

## Acceptance criteria

1. (MUST FAIL FIRST) The backfill is invocable from the `frob` CLI. Fails
   today: no parser, no runner, four in-module references only.
2. Running it against the real ledger repairs the two `T-draft-0bd874ac`
   attachment paths on `tickets/T-2195`, and an unscoped
   `frob check --only coverage` afterwards reports **0** COV004 findings
   (currently 2).
3. The attachment FILES are byte-identical afterwards -- verify against the
   recorded sha256, which is now correct post-T-2239. Only the ledger `path:`
   field changes.
4. MUST-STILL-PASS CONTROL: a correctly-recorded attachment is left untouched,
   and a draft id with no resolvable successor is REPORTED, not guessed. Both
   behaviours already have tests from T-2226 -- they must still pass.
5. A dry-run / report-only mode exists, or an explicit reason is given for its
   absence. This mutates the ledger; being able to see the plan first is the
   difference between a repair and a hope.

## Scope note

`src/frob/tickets/_draft_finalize.py` owns the function. The CLI wiring will
need its parser and runner -- the T-2217 precedent is that a dispose-style flag
needed `src/frob/_cli_parsers/_<area>.py`, an `AppConfig` field in
`src/frob/app/config.py`, and registration in
`src/frob/app/_config_external.py`. Read the existing wiring for a neighbouring
verb before assuming which files apply, and widen scope with a measured reason
rather than guessing from module names.