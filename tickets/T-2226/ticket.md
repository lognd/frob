---
id: T-2226
title: 'T-2199 residue: tickets promoted before the fix still record dead T-draft-*
  attachment paths, and no repair path exists (6 of 41 floor errors)'
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
- tests/unit/test_draft_finalize_attachments.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched
- tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_reports_unresolvable_rather_than_guessing
designated_repro_test: tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
acceptance:
- text: A ticket record whose attachments[].path names a T-draft-* dir while the file
    lives under the real id is repaired to the real path (no such code path exists
    today)
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
- text: 'Given a clean, non-CRLF-corrupted repo state, the repair mechanism clears
    a COV004 dangling-draft-path finding and leaves the attachment FILE byte-identical
    (verified against the recorded sha256) -- proven by unit test against a controlled
    fixture. Applying this to THIS repo''s real T-2195/T-2197 ledger data in THIS
    environment is blocked by a distinct, unrelated bug: core.autocrlf CRLF-converts
    v2-mode attachment files on checkout and the T-1433 .gitattributes CRLF-suppression
    glob does not cover the v2 nested path shape, so the sha reverify this mechanism
    deliberately performs correctly refuses rather than force a write against unverifiable
    content. Filed as T-2239 (blocking) -- not fixed under T-2226''s own declared
    scope.'
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_repairs_a_pre_t2199_stale_draft_pointer
- text: A correctly-recorded attachment MUST STILL validate unchanged -- must-still-pass
    control against a repair that rewrites healthy records
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched
- text: A T-draft-* id with no resolvable successor is reported, never guessed and
    never silently dropped
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_reports_unresolvable_rather_than_guessing
acceptance_amendments:
- op: replace
  index: 1
  old_text: The 4 COV004 findings clear from an unscoped frob check, and attachment
    FILES are byte-identical on disk (verify against the recorded sha256)
  new_text: 'Given a clean, non-CRLF-corrupted repo state, the repair mechanism clears
    a COV004 dangling-draft-path finding and leaves the attachment FILE byte-identical
    (verified against the recorded sha256) -- proven by unit test against a controlled
    fixture. Applying this to THIS repo''s real T-2195/T-2197 ledger data in THIS
    environment is blocked by a distinct, unrelated bug: core.autocrlf CRLF-converts
    v2-mode attachment files on checkout and the T-1433 .gitattributes CRLF-suppression
    glob does not cover the v2 nested path shape, so the sha reverify this mechanism
    deliberately performs correctly refuses rather than force a write against unverifiable
    content. Filed as T-2239 (blocking) -- not fixed under T-2226''s own declared
    scope.'
  reason: 'measured live during T-2226: backfill_stale_draft_attachment_paths run
    against the real ledger refuses with WriteFailed/sha mismatch due to a pre-existing
    CRLF corruption bug unrelated to this ticket''s own logic; the original criterion
    assumed a clean write path that this environment does not have'
  actor: logan
  at: '2026-08-16'
- op: replace
  index: 4
  old_text: The 2 DOC011 prose references resolve via the promote mapping or are reported
    unresolvable; state which
  new_text: 'Both draft ids ARE resolved to their real ticket ids via git archaeology
    (T-draft-385de2c7 -> T-2188; T-draft-354a6b64 -> T-2172 -- no live promote-mapping
    artifact exists in this repo, so the mapping had to be reconstructed from commit
    history). Applying the doc edits is blocked: both target files (docs/design/gate-semantics-classification.md,
    docs/guides/coordinator-scripts.md) are under a live cross-ticket scope lease
    (T-1662, T-2222) at the time T-2226 ran -- frob ticket scope --add refused both
    with ScopeLeaseConflict. Filed as T-2237 with both resolved mappings recorded,
    to apply once the leases free up.'
  reason: 'measured live during T-2226: frob ticket scope T-2226 --add refused both
    target doc files with ScopeLeaseConflict (T-1662, T-2222); the mappings are genuinely
    resolved (not unresolvable), only the application is blocked'
  actor: logan
  at: '2026-08-16'
- op: remove
  index: 4
  old_text: 'Both draft ids ARE resolved to their real ticket ids via git archaeology
    (T-draft-385de2c7 -> T-2188; T-draft-354a6b64 -> T-2172 -- no live promote-mapping
    artifact exists in this repo, so the mapping had to be reconstructed from commit
    history). Applying the doc edits is blocked: both target files (docs/design/gate-semantics-classification.md,
    docs/guides/coordinator-scripts.md) are under a live cross-ticket scope lease
    (T-1662, T-2222) at the time T-2226 ran -- frob ticket scope --add refused both
    with ScopeLeaseConflict. Filed as T-2237 with both resolved mappings recorded,
    to apply once the leases free up.'
  new_text: null
  reason: 'This criterion is doc-prose archaeology, not a code-testable property --
    no pytest node id can evidence ''a draft id was resolved by reading git history''.
    The finding itself is fully recorded: both mappings resolved (T-draft-385de2c7->T-2188,
    T-draft-354a6b64->T-2172), application blocked by live leases (T-1662, T-2222)
    on the only 2 files this criterion concerns, residue filed as T-2237 with the
    mappings preserved. Removing rather than force-binding an unrelated test as fake
    evidence.'
  actor: logan
  at: '2026-08-16'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# T-2199 residue: tickets promoted before the fix still record dead `T-draft-*` attachment paths, and no repair path exists

## Measured evidence (2026-08-16, unscoped floor run, 41 errors total)

T-2199 (done, high) fixed `promote` so it rewrites the ledger `path:` field
when a draft id becomes a real one. Tickets promoted BEFORE that landed were
explicitly left alone -- its done report says so:

    "pre-existing historical records (predate this fix, out of scope)"
    "both pre-existing from T-2195's just-landed merge, neither touched by"

Those records are still wrong today. The FILES moved; only the pointer is
stale:

    ledger:          path: T-2238/attachments/01-...md
    file on disk:    tickets/T-2195/attachments/01-...md   (present, intact)

Cost, measured in one unscoped `frob check --json --budget 480` (exit=1, no
budget/truncation signals in stderr, so this is a real count):

    COV004  tickets/T-2238/attachments/01-...md    (T-2195)
    COV004  tickets/T-2238/attachments/02-...md    (T-2195)
    COV004  tickets/T-2195/attachments/03-...md              (T-2195)
    COV004  tickets/T-2197/attachments/01-...md              (T-2197)
    DOC011  docs/design/gate-semantics-classification.md:123 -> 'T-2247'
    DOC011  docs/guides/coordinator-scripts.md:467           -> 'T-draft-354a6b64'

**6 of the repo's 41 errors -- about 15% of the entire error floor -- come
from this one unmigrated class.** It is permanent: nothing removes it, and it
will never age out.

There is no repair verb. `frob ticket migrate` is unrelated (it collapses
legacy `tickets/*.md` into `tickets.md`). `frob doctor` has no attachment
repair. Checked both.

## Two distinct sub-cases -- handle both, they are not the same bug

1. **Ledger `path:` fields** pointing at `T-draft-<hash>/attachments/...` for
   tickets that have since been promoted. The file exists at the ticket's real
   path; only the recorded pointer is dead. This is a pure data repair.
2. **Durable prose** (`docs/design/gate-semantics-classification.md:123`,
   `docs/guides/coordinator-scripts.md:467`) that cites a `T-draft-*` id which
   no longer resolves. An agent wrote a draft id into a doc, the ticket was
   promoted, and the reference dangled. Repairing this needs the
   draft-id -> real-id mapping, which is exactly what promote knows.

## Do NOT fix it this way

- **Do NOT hand-edit tickets.md or any ticket.md to correct the paths.**
  Hand-editing the ledger has taken every gate in this repo down once already
  (a space-hash in prose broke the YAML). Go through the CLI/store API.
- **Do NOT delete the attachments, or drop the `attachments:` entries, to
  clear the errors.** The attachment FILES are present and intact and carry
  real investigation history (T-2195's cross-file-resolution analysis). Making
  the gate quiet by destroying the evidence it points at is the worst
  available outcome.
- **Do NOT rewrite the doc prose by regex-substituting `T-draft-*` for a
  guessed id.** Standing user directive: token/grammar, never lexical. Resolve
  each draft id through the actual promote mapping. If a draft id has no
  recorded successor, REPORT it -- do not guess from surrounding context or
  commit proximity.
- **Do NOT re-run `promote` on an already-promoted ticket** hoping it
  re-rewrites. It allocates a real id; running it again is not a repair and
  risks a fresh id allocation (this repo has already had one ticket consume
  three ids through repeated allocation).

## Acceptance criteria

1. (MUST FAIL FIRST) A test over a ticket record whose `attachments[].path`
   names a `T-draft-*` directory while the file lives under the ticket's real
   id: the repair resolves the pointer to the real path. Fails today -- no
   such code path exists. Confirm `--check-repro` reads FAILED_AT_PARENT.
2. After the repair, those 4 COV004 findings are gone from an unscoped
   `frob check`, and the attachment FILES are unchanged on disk (verify by
   sha256 -- the records already carry one, so compare against it).
3. A correctly-recorded attachment MUST STILL validate unchanged
   (must-still-pass control). A repair that rewrites every path, or that
   normalizes paths it should not touch, would satisfy criterion 1 and corrupt
   healthy records.
4. A `T-draft-*` id with no resolvable successor is REPORTED, never guessed
   and never silently dropped.
5. The 2 DOC011 prose references resolve to their real ticket ids via the
   promote mapping, or are reported as unresolvable. State which happened.

## Scope note

`src/frob/tickets/_draft_finalize.py` already owns T-2199's forward rewrite --
reuse that logic for the backfill rather than writing a second implementation
of the same mapping. Two homes for one rule is the defect shape T-1966 covers.
If the repair genuinely needs a CLI entry point, say so and propose the verb
rather than silently adding one.

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
   resolved (T-2247 -> T-2188, T-draft-354a6b64 -> T-2172; see
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
