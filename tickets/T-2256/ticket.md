---
id: T-2256
title: Repoint the 28 orphaned COV003 evidence ids from T-2240's legitimate test retirement
  (47% of the error floor, 11 archived tickets)
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
- tickets/archive
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: An unscoped frob check reports 0 COV003 findings naming tests/unit/test_makefile_coverage.py
    (currently 28)
  evidence: []
- text: Every repointed citation names a test carrying the SAME claim as the deleted
    node; state old node, new node, and shared claim per ticket
  evidence: []
- text: Any orphaned citation with no surviving equivalent is reported explicitly,
    never repointed to an approximation
  evidence: []
- text: 'MUST-STILL-PASS: the surviving 195-line test file is unchanged, and the floor
    drops by the number cleared -- verified by unscoped check with gate-summary present
    both times'
  evidence: []
- text: No production code path changes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# Repoint the 28 orphaned COV003 evidence ids left by T-2240's legitimate test retirement -- 47% of the current error floor

## Measured evidence (2026-08-16)

Unscoped `frob check --json` (43 results, `gate-summary` present, all 24
`gate:*` families -- coverage verified, not a budget-truncated read):

    ERRORS 59
      28  gate:COV:COV003   <- all naming tests/unit/test_makefile_coverage.py
       7  gate:TICK:TICK004
       6  gate:ARCH:ARCH001
       4  frob-cycle
       ...

28 of 59 errors -- 47% of the floor -- are one class.

T-2240 (`dcb07727d8ce`) rewrote `tests/unit/test_makefile_coverage.py` from 924
to 195 lines, retiring the Makefile-text-slicing tests after wiring
`make coverage` to `frob coverage --full`. **That retirement was correct and
must not be undone**: those tests asserted against Makefile recipe TEXT, which
is exactly the coupling T-1382 exists to remove.

The removal orphaned evidence bound on 11 tickets, ALL of them archived
(verified: 11 of 11 resolve under `tickets/archive/<id>/ticket.md`, none in the
active tree):

    T-1205 T-1235 T-1335 T-1353 T-1362 T-1363 T-1373 T-1397 T-1426 T-1433 T-1526

## Established precedent -- follow it

T-1941 (done) resolved this exact class: "COV003: T-0185 evidence references a
test deleted by the exhaustive-research skill/agent removal". Its approach,
from its own done report:

- repoint stale evidence with `frob ticket evidence --replace` on the archived
  tickets;
- record a `frob:no-behavior-change reason="..."` waiver, because the change is
  ledger-only (`tickets.md` / `tickets/archive/**/ticket.md`) and touches no
  production code path, so there is no defect for a designated repro test to
  reproduce;
- where a deleted test carried a specific CLAIM, it named the surviving test
  that carries the same claim rather than picking any passing node.

That last point is the substance of this work. Repointing is not "find any
green test"; it is "find the test that still proves what the archived ticket
cited".

## Do NOT fix it this way

- **Do NOT restore the deleted tests.** They asserted on Makefile recipe text.
  Bringing them back would re-couple the test suite to the Makefile and undo
  T-2240, which is a leaf of the standing "decouple frob from the Makefile"
  epic.
- **Do NOT repoint to an arbitrary passing test to silence COV003.** That
  fabricates a historical record: the archived ticket would then claim proof
  from a test that never proved its point. Prefer leaving a finding visible
  and reported over a false citation.
- **Do NOT hand-edit `tickets/archive/**/ticket.md` or `tickets.md`.**
  Hand-editing the ledger has taken every gate in this repo down once. Use
  `frob ticket evidence --replace`, as T-1941 did.
- **Do NOT delete the citing tickets' evidence entries wholesale.** An archived
  ticket with no evidence is a weaker record than one citing a surviving
  equivalent.
- **Do NOT change COV003 so it stops firing on archived tickets.** T-1946
  deliberately made the sibling land guard load the archive as an authoritative
  source; narrowing the gate instead of fixing the data would silently hide
  this whole class. If you believe that policy is wrong, say so and file it --
  do not implement it here.

## Acceptance criteria

1. (MUST FAIL FIRST) An unscoped `frob check` reports 0 COV003 findings naming
   `tests/unit/test_makefile_coverage.py`. Currently 28.
2. Every repointed citation names a test that carries the SAME claim the
   deleted node carried. For each of the 11 tickets, state the old node, the
   new node, and the claim they share.
3. Any orphaned citation with NO surviving equivalent is REPORTED explicitly,
   not repointed to an approximation. Say which and why -- a smaller honest
   repointing beats a complete-looking one.
4. MUST-STILL-PASS CONTROL: the surviving 195-line
   `tests/unit/test_makefile_coverage.py` is unchanged, and the total error
   floor drops by the number of findings cleared -- verify by unscoped
   `frob check --json` before and after, with `gate-summary` present in both
   (a budget-truncated run reports a false improvement; that has happened here).
5. No production code path changes. If one seems necessary, stop and report.

## Scope note

Ledger-only: `tickets/archive/**` and `tickets.md`, driven through
`frob ticket evidence --replace`. Note `docs/guides/agent-playbook.md:924`
already documents the deletion-filter land rule; the guard that should have
PREVENTED this is T-2255 (critical, filed) -- this ticket is the cleanup, not
the prevention. Do not conflate them.
