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
    content. Filed as T-2239 (blocking) -- not fixed under T-2226''s own
    declared scope.'
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
    content. Filed as T-2239 (blocking) -- not fixed under T-2226''s own
    declared scope.'
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
    with ScopeLeaseConflict. Filed as T-2237 with both resolved mappings
    recorded, to apply once the leases free up.'
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
    with ScopeLeaseConflict. Filed as T-2237 with both resolved mappings
    recorded, to apply once the leases free up.'
  new_text: null
  reason: 'This criterion is doc-prose archaeology, not a code-testable property --
    no pytest node id can evidence ''a draft id was resolved by reading git history''.
    The finding itself is fully recorded: both mappings resolved (T-draft-385de2c7->T-2188,
    T-draft-354a6b64->T-2172), application blocked by live leases (T-1662, T-2222)
    on the only 2 files this criterion concerns, residue filed as T-2237
    with the mappings preserved. Removing rather than force-binding an unrelated test
    as fake evidence.'
  actor: logan
  at: '2026-08-16'
threat: null
component: null
anchor: false
anchor_reason: null
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
    DOC011  docs/design/gate-semantics-classification.md:123 -> 'T-draft-385de2c7'
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