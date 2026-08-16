## Done report

Implemented `backfill_stale_draft_attachment_paths` in
src/frob/tickets/_draft_finalize.py, reusing T-2199's own
`_relocate_attachment_records` primitive rather than reimplementing the
rename/reverify logic (per the ticket's own scope note). For every ticket
in the merged ledger, any `attachments[].path` whose leading path segment
is a draft id other than the ticket's own current id is treated as a
pre-T-2199 dangling pointer and relocated -- no external draft->real-id
map is needed for this sub-case, since the ticket object itself already
carries both ends of the mapping.

3 new tests added/passing (repair, must-still-pass-untouched control,
report-not-guess-on-genuinely-lost-file). Repro designated and verified
FAILED_AT_PARENT: committed the test alone first (8b23ae666), confirmed a
real ImportError/collection failure via a detached checkout at that
commit (backfill_stale_draft_attachment_paths did not exist yet), then
committed the fix separately (b73efb702). `--designate-repro` against
8b23ae666 recorded FAILED_AT_PARENT directly.

## Two blockers found while verifying acceptance -- NOT fixed under this
## ticket's scope, both filed as residue

1. Running the backfill against this repo's REAL T-2195/T-2197 ledger
   data in THIS environment refuses (WriteFailed, sha256 mismatch) rather
   than relocating -- correctly, by design. Root cause, confirmed by
   direct measurement: `core.autocrlf=true` is set (locally and
   globally) and converts checked-out attachment files to CRLF; the
   T-1433 `.gitattributes` CRLF-suppression glob
   (`tickets/attachments/** -text`) only matches the OLD v1 flat
   attachments layout, not v2's nested `tickets/<id>/attachments/**`
   shape, so it never protects these files. Directly reproduced: the
   LF-normalized sha256 of T-2195's already-correctly-pathed attachment
   03 EQUALS the recorded sha256; the raw on-disk (CRLF) sha256 does not.
   This is ALSO why 2 of the ticket's "4 COV004" findings (T-2195's
   attachment 03, T-2197's attachment 01) were never a draft-path issue
   at all -- their paths are already correct; they fire purely from this
   CRLF corruption. Filed T-2239 (high) for the .gitattributes
   glob fix; acceptance [3] there is "T-2226's two still-unresolved
   T-2238 records are re-attempted and confirmed relocated
   once this lands".

2. The 2 DOC011 dangling-`T-draft-*` doc citations: both mappings ARE
   resolved (T-draft-385de2c7 -> T-2188, T-draft-354a6b64 -> T-2172; see
   the filed ticket for the exact git-archaeology evidence -- no live
   promote-mapping artifact exists anywhere in this repo, contrary to
   this ticket's assumption; the mapping had to be reconstructed from
   commit history since one promotion was a hand id-field edit and the
   other was a land-ordering race between a doc edit and the renumber
   scan). Could not apply the doc edits: both target files
   (docs/design/gate-semantics-classification.md,
   docs/guides/coordinator-scripts.md) are under a LIVE cross-ticket
   scope lease (T-1662, T-2222) -- `frob ticket scope --add` refused both
   with ScopeLeaseConflict. Filed T-2237 (medium) with both
   resolved mappings recorded so the follow-up needs no re-archaeology.

## Acceptance criteria status

1. DONE -- repair code exists, unit-tested, FAILED_AT_PARENT confirmed.
2. PARTIAL -- the 4 COV004 findings do NOT all clear in this environment;
   blocked by the filed CRLF/.gitattributes bug (blocker 1 above), not by
   anything in this ticket's own logic. Attachment files ARE confirmed
   unchanged on disk (the backfill never wrote anything against the real
   ledger -- it refused, by design, rather than force a write against
   content it could not sha-verify).
3. DONE -- must-still-pass control test passes; a correctly-recorded
   attachment is never inspected past the `is_draft_id` filter.
4. DONE -- unresolvable pairs are reported in `unresolved`, never
   guessed/dropped; covered by test_reports_unresolvable_rather_than_guessing.
5. DONE -- both draft ids resolved via git archaeology (stated which);
   application blocked by live leases, residue filed (T-2237).

### Changed
```
 src/frob/tickets/_draft_finalize.py           |  93 +++++++++++++
 tests/unit/test_draft_finalize_attachments.py | 183 +++++++++++++++++++++++++-
 tickets/T-2226/ticket.md                      |  17 ++-
 tickets/T-2237/ticket.md            |  73 ++++++++++
 tickets/T-2239/ticket.md            |  69 ++++++++++
 5 files changed, 428 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_reports_unresolvable_rather_than_guessing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH001@src/frob/tickets/_draft_finalize.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_draft_finalize.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2238/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2238/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC002@src/frob/tickets/_draft_finalize.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2226/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2226/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/tickets/_draft_finalize.py, PRE001@tickets/T-2226, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@src/frob/tickets/_draft_finalize.py
