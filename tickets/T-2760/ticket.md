---
id: T-2760
title: 'Two tickets can own the same (rule, file) finding: the duplicate check compares
  titles, not finding identity'
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_evidence.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/_config_external.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/test_tickets.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets-data-storage.md
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_tickets.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2760: add structured (rule,file) finding-identity duplicate detection
    at filing and start time'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: docs for new finding-identity field/CLI flag
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: docs for new finding-identity field/CLI flag
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured, 2026-08-20

Two tickets independently owned, worked, and landed a fix for the SAME
finding:

    T-2757  'post-land sweep regression from an unattributed source
             (sweep spawned by T-2741)'          origin: agent
    T-2759  'DOC011: docs/modules/tickets-verify-sweep.md cites phantom
             T-2736 without a waiver'            origin: human

Both cite DOC011 on `docs/modules/tickets-verify-sweep.md`, both name the
phantom `T-2736`, both landed. The second agent discovered the collision
only when its `git merge main` silently absorbed the other's identical
content fix -- its own land commit shows NO diff to the doc, only its
regression tests.

Nothing detected the duplication at filing time, at start time, or at
land time.

## Why the existing guard did not catch it

`frob ticket new` DOES have a duplicate check -- it refused one of my own
filings earlier the same day with a `100% match` on the title. But it
compares TITLES, and these two titles share no words: one is the sweep's
generated "post-land sweep regression from an unattributed source"
phrasing, the other is a hand-written description of the actual defect.

So the guard is keyed on the wrong identity. What makes these duplicates
is not the title -- it is the `(rule, file)` finding they both own.

## Cost

Real but bounded here: one agent spent a full triage cycle on a line
another had already fixed. It resolved cleanly because git merged the
identical content, but that was luck about the shape of the fix, not a
property of the system. Two agents editing the same line differently
would have produced a conflict at best.

The deeper cost is that a finding can have two owners and neither knows.
This repo's whole discipline is that unaccounted work is a build failure;
DOUBLE-accounted work is the same class of bookkeeping error and is
currently invisible.

## What to build

At filing time, and again at `frob ticket start`, check whether any open
ticket already declares the same `(rule, file)` finding identity, and
refuse (or warn loudly and name it) if so -- the same posture the
title-duplicate check already takes. The sweep's own auto-filing path
must be covered, since that is where generated titles diverge most from
hand-written ones.

## Positive controls, both directions

- two tickets naming the same (rule, file) finding: the second is refused
  or loudly flagged, naming the first
- two tickets naming DIFFERENT findings in the same FILE are both allowed
  -- file-level matching would be too coarse and would block legitimate
  parallel work
- the existing title-based duplicate check keeps working unchanged

## Note

Do not fix this by making the sweep title its tickets after the finding.
That would make the title check accidentally cover this case while
leaving the underlying identity unmodelled, and it would break the first
time a ticket legitimately owns more than one finding.
