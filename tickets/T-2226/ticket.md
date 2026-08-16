---
id: T-2226
title: 'T-2199 residue: tickets promoted before the fix still record dead T-draft-*
  attachment paths, and no repair path exists (6 of 41 floor errors)'
state: queued
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
designated_repro_test: null
acceptance:
- text: A ticket record whose attachments[].path names a T-draft-* dir while the file
    lives under the real id is repaired to the real path (no such code path exists
    today)
  evidence: []
- text: The 4 COV004 findings clear from an unscoped frob check, and attachment FILES
    are byte-identical on disk (verify against the recorded sha256)
  evidence: []
- text: A correctly-recorded attachment MUST STILL validate unchanged -- must-still-pass
    control against a repair that rewrites healthy records
  evidence: []
- text: A T-draft-* id with no resolvable successor is reported, never guessed and
    never silently dropped
  evidence: []
- text: The 2 DOC011 prose references resolve via the promote mapping or are reported
    unresolvable; state which
  evidence: []
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

    ledger:          path: T-draft-0bd874ac/attachments/01-...md
    file on disk:    tickets/T-2195/attachments/01-...md   (present, intact)

Cost, measured in one unscoped `frob check --json --budget 480` (exit=1, no
budget/truncation signals in stderr, so this is a real count):

    COV004  tickets/T-draft-0bd874ac/attachments/01-...md    (T-2195)
    COV004  tickets/T-draft-0bd874ac/attachments/02-...md    (T-2195)
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
