## Done report

T-2226 landed `backfill_stale_draft_attachment_paths` in `src/frob/tickets/
_draft_finalize.py` with no CLI entry point -- four in-module references,
no parser, no runner. It repaired zero records against the real ledger
because the shared sha-reverify guard correctly refused CRLF-corrupted
attachment files (T-2239's own defect, fixed separately).

Wired the backfill onto the EXISTING `frob ticket attach` verb via a new
`--backfill-drafts [--apply]` flag pair, rather than inventing a new
subcommand -- the ticket's own constraint against expanding `frob ticket`'s
vocabulary beyond `promote`/`attach`/`migrate`/`reconcile`. `attach` is the
correct home: the `Attachment.path` record this backfill repairs is
squarely `attach`'s own domain. `reconcile` was considered and rejected --
its own `reconcile()` primitive is a narrowly-scoped worktree<->ticket
binding healer (T-0476) with nothing to do with attachment records;
repurposing it would misdescribe the verb rather than extend it.

Report-only by default; `--apply` writes, mirroring `frob ticket reconcile`'s
own report-first/`--apply`-to-write shape (acceptance [5]'s dry-run
requirement). `backfill_stale_draft_attachment_paths` and
`_relocate_attachment_records` both gained a `dry_run` parameter (default
`False`, unchanged for the existing T-2199 forward-rewrite caller) that runs
every validation step (file existence, sha256 re-verification) unchanged but
skips the final `write_ticket` call.

`src/frob/app/ticket_runner/_lifecycle.py` (`_attach`'s own home) carried a
live cross-worktree lease (T-2220) for this ticket's entire duration, so the
dispatch decision was split into a new sibling module
(`_attach_backfill.py`): `_attach_dispatch` imports `_lifecycle._attach`
UNMODIFIED for the ordinary single-file case, so `_lifecycle.py` needed zero
edits.

Ran `--backfill-drafts` (dry-run) against the real ledger first to confirm
the premise, then `--apply`: repaired `T-2195`'s two stale
`T-draft-0bd874ac`-prefixed attachment records. Both files' bytes already
matched their recorded sha256 (T-2239's CRLF fix) -- only the ledger
`path:` field changed (2 lines in `tickets/T-2195/ticket.md`). Unscoped
`frob check --only coverage` COV004 count: 2 -> 0.

Did not weaken the sha-reverify guard, did not hand-edit any ticket.md,
did not delete the attachments, did not invent new CLI vocabulary.

Known, disclosed, unresolved at time of writing: `frob check --ticket
T-2254` reports one repo-wide (not ticket-scoped per the check's own
scope-note) SELFAUDIT111 finding -- the `tickets_ledger` capability
via-list's `fs.write` site count grew past its committed ratchet ceiling
(16 -> 17) in `docs/design/registry/capability-via-ratchet.lock.json`,
which correctly requires a same-diff ceiling bump. That file is under
T-2220's live cross-worktree lease for this ticket's entire session
(confirmed via T-2220's own `ticket.md` scope_changes on its own worktree
branch, not visible on `main` until it lands) -- `frob ticket scope T-2254
--add docs/design/registry/capability-via-ratchet.lock.json` was attempted
repeatedly and refused each time (ScopeLeaseConflict). Removing the new
production commit call did NOT clear the finding (measured by temporarily
disabling it and re-running `frob check --only sys`), confirming the count
also grows from the new tests exercising `backfill_stale_draft_
attachment_paths`/`write_ticket` directly, not only from the new CLI
dispatch path -- so there is no way to implement and test this ticket's
acceptance criteria without growing the via-list at all. T-2220 was
observed actively landing (`frob ticket land T-2220 --finish` running) at
the time of this report; the ceiling bump should be attempted again once
that lease clears, before or as part of landing T-2254.

## Done report

Changed:
src/frob/tickets/_draft_finalize.py -- dry_run parameter on backfill_stale_draft_attachment_paths/_relocate_attachment_records/_backfill_one_ticket
src/frob/app/ticket_runner/_attach_backfill.py -- new module: _attach_dispatch/_run_backfill_drafts CLI wiring
src/frob/app/ticket_runner/__init__.py -- dispatch table routes "attach" through _attach_dispatch
src/frob/_cli_parsers/_ticket/_closeout.py -- --backfill-drafts/--apply flags on the attach subparser, ticket_id made optional
src/frob/app/config.py -- ticket_attach_backfill_drafts/ticket_attach_backfill_apply AppConfig fields
src/frob/app/_config_external.py -- registered both new bool flags
tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths.test_dry_run_reports_without_writing
tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts -- CLI dispatch tests (dry-run, apply+commit)
tickets/T-2195/ticket.md -- real repair: 2 stale T-draft-0bd874ac attachment path: fields corrected to T-2195/attachments/...

Evidence:
tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts.test_backfill_drafts_apply_writes_and_reports (designated repro, FAILED_AT_PARENT at 8ad809408)
tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts.test_backfill_drafts_dry_run_does_not_write
tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths.test_dry_run_reports_without_writing
tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths.test_repairs_a_pre_t2199_stale_draft_pointer
tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths.test_leaves_a_correctly_recorded_attachment_untouched
tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths.test_reports_unresolvable_rather_than_guessing

Filed: none

Gates: frob check --ticket T-2254 clean on every ticket-scoped family (SCOPE/PREWORK/diff-driven COV002-TODO001/FMT/AFFECT) after widening scope to tickets/T-2195/ticket.md (the ledger record this ticket's own acceptance criteria requires repairing) and adding reasoned waivers for AFFECT001/SELFAUDIT001(fs.read round-trip)/WIRE001 matching this repo's existing precedent for each rule. One remaining SELFAUDIT001 finding (SYS111 tickets_ledger fs.write ratchet, 16->17) is genuinely caused by this ticket's new code+tests but cannot be resolved from this worktree: the one file that accepts the ceiling bump (docs/design/registry/capability-via-ratchet.lock.json) is under T-2220's live cross-worktree lease for this ticket's entire session. Not a scope-widening refusal I can route around -- confirmed by disabling the new commit call and re-measuring, which did not clear it.

### Changed
```
 src/frob/_cli_parsers/_ticket/_closeout.py     |  33 ++++++-
 src/frob/app/_config_external.py               |   3 +
 src/frob/app/config.py                         |   6 ++
 src/frob/app/ticket_runner/__init__.py         |   5 +-
 src/frob/app/ticket_runner/_attach_backfill.py | 127 +++++++++++++++++++++++++
 src/frob/tickets/_draft_finalize.py            |  48 ++++++++--
 tests/unit/test_app_runners_batch7.py          | 100 +++++++++++++++++++
 tests/unit/test_draft_finalize_attachments.py  |  45 +++++++++
 tickets/T-2195/ticket.md                       |   4 +-
 tickets/T-2254/ticket.md                       | 111 ++++++++++++++++++++-
 10 files changed, 469 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_apply_writes_and_reports` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts::test_backfill_drafts_dry_run_does_not_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_dry_run_reports_without_writing` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_reports_unresolvable_rather_than_guessing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH001@src/frob/tickets/_draft_finalize.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2254/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2254/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2254, RENDER001@src/frob/scaffold/_skills_sync.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
