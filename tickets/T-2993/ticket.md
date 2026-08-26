---
id: T-2993
title: 'Ticket-narrative comment blocks: 1728 blocks / 11116 lines of T-id archaeology
  in code, still being written'
state: in-progress
kind: docs
origin: human
created: '2026-08-26'
priority: high
parent: T-2994
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_narrative_blocks.py
- src/frob/narrative/**
- src/frob/__main__.py
- docs/design/registry/check-coverage.yaml
- tests/test_narrative_blocks.py
- tests/test_narrative_migrate.py
- docs/modules/gates.md
- docs/commands/narrative.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_narrative_blocks.py
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/narrative/**
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/__main__.py
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_narrative_blocks.py
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_narrative_migrate.py
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gates.md
  reason: T-2993 detector (NARR001) + migration verb (frob narrative move) + fixtures;
    gates/__init__.py wiring deferred, leased by T-2986
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/commands/narrative.md
  reason: T-2993 doc page for the new frob narrative verb + NARR001 detector
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2994
  reason: 'T-2994 owns the one doctrine: code and docs carry utility, tickets carry
    narrative'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Third form of the same doctrine as T-2987 (waiver-reason bloat) and T-2988
(docstring archaeology): free-standing `# T-####: <narrative>` comment blocks
that record WHY a change was made rather than what the code does.

MEASURED 2026-08-26:

| location          | blocks | lines  | avg  | largest |
|-------------------|--------|--------|------|---------|
| src/ python       |   1216 |  8,190 |  6.7 | 130     |
| tests/ python     |    309 |  1,514 |  4.9 |  45     |
| design/*.strata   |    203 |  1,412 |  7.0 |  53     |
| TOTAL             |   1728 | 11,116 |      |         |

`design/*.strata` is the worst by ratio: 1,851 of 2,842 lines are comments (65%).
Largest individual blocks: 130 lines in `src/frob/vet/_capability_typescript_
bindtable.py`, 105 in `src/frob/gates/_waive.py`, 67 in `_capability_python.py`.

THIS IS STILL BEING CREATED. The owner flagged it from an IN-FLIGHT agent's diff,
not from old code. So a one-time sweep will not hold -- it regrows at the rate
agents write it. Whatever ships here needs a standing gate, on the same
burn-then-promote pattern the WARN families use, or it is a temporary cleanup
rather than a fix.

THE JUDGEMENT THAT MAKES THIS HARD -- do not skip this. The blocks are NOT
uniformly noise. The example the owner cited (`_socketd.py`, T-2961) contains
both kinds in one block:

  KEEP (illuminates the code for whoever edits it next): "a CLASS statement
  referencing a missing base at module scope raises AttributeError the instant
  the module is IMPORTED, not when the daemon is used -- unlike the fcntl/msvcrt
  pattern used for FUNCTIONS." Someone modifying that guard needs this. Without
  it they will "simplify" the structure and reintroduce an import-time crash.

  MOVE (records how we got here): the T-2918/T-2934/T-2952/T-2953 cross-
  references, the historical framing, the comparison to what the repo did
  before.

So the test is the same one T-2988 established for docstrings: does this text
help someone about to MODIFY OR REUSE this code, or does it explain why we
arrived here? The first stays (trimmed to the point). The second moves to the
ticket that already owns it -- and the block already names that ticket, which is
what makes this mechanically tractable at all.

ON AUTOMATING THIS IN `land` -- the owner asked whether land could move
ticket-prefixed blocks automatically. RECOMMENDATION: NO, not in land. Reasons,
grounded in this repo's own recent history:

- Land is already the most contended and most failure-prone step in the system.
  In a single day it produced: a `state=done` written with zero code on main, tip
  -drift refusals, DirtyMain deadlocks, a quarantine deadlock that took five land
  attempts to clear, and multiple timeouts. Adding source-rewriting to that path
  enlarges the blast radius of the exact step we spent the day making faster and
  safer.
- A land that rewrites source means THE COMMIT THAT LANDS IS NOT THE DIFF THAT
  WAS REVIEWED. That is a reviewability regression regardless of how good the
  rewrite is.
- If the migration picks the wrong ticket or hits the archived-ticket write
  hazard, it corrupts BOTH the code and the ledger at the least recoverable
  moment.

BETTER SHAPE, three parts:
1. A DETECTOR that flags over-long T-id narrative blocks, so the pattern cannot
   regrow. Ship it at WARN, burn the existing 1,728 down, then promote to ERROR
   -- the pattern proven on TICK011 under T-2372.
2. A DELIBERATE MIGRATION COMMAND (a `frob refactor`-family verb, not land) that
   moves one block into its named ticket and leaves a one-line reference behind.
   Author-invoked, reviewable in the diff, idempotent.
3. Land may CHECK (refuse or warn on a violation) but must never REWRITE.

MIGRATION HAZARDS, all previously paid for in this repo:
- Most cited tickets are ARCHIVED, and `frob ticket body` on a done ticket has
  written to the ACTIVE path and produced a DuplicateId that downed every ledger
  load repo-wide. Prove the archived-write path on ONE ticket before any batch.
- Idempotency: running the migration twice must not append the block twice.
- MOVE, NEVER DELETE. This is institutional memory; several agents this drive
  avoided repeating a landed mistake because such a note existed.
- `uv run frob ticket list` must exit 0 after every batch.

ACCEPTANCE
- A detector flags T-id narrative blocks over a stated line threshold, with a
  must-fire fixture (a long archaeology block) and a must-stay-quiet fixture (a
  short block that genuinely explains the code, of the KEEP kind above).
- A migration verb moves a block into its named ticket, leaves a reference, is
  idempotent, and is proven on the `_socketd.py` T-2961 block specifically --
  keeping the import-time-crash explanation in place and moving only the
  history.
- Land does NOT rewrite source. If land gains a check, it refuses or warns only.
- Report before/after block counts and line totals for all three locations
  (src/, tests/, design/), and confirm no narrative was deleted rather than
  relocated.
