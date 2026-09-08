---
id: T-4287
title: 'reopening a terminal ticket strands every worktree that forked before it:
  the land guard cannot tell an audited reopen from an accidental merge resurrection'
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_reporting.py
- tests/unit/test_land_sibling_regression.py
- tests/unit/test_reopen_ticket.py
- docs/modules/tickets.md
scope_breadth_ack: true
scope_breadth_ack_reason: src/frob/tickets/_land.py is already a documented god-module
  (T-1651/LARGE001/ARCH102 waivers on this same file) with dozens of private-helper
  call edges into sibling _land_*.py/_store.py/_journal.py modules and frob:doc anchors
  scattered across 6+ docs/modules/*.md files -- this predates T-4287 and is unrelated
  to its fix (the T-1914 sibling-state-regression guard plus the reopen-verb warning).
  Widening scope to close every one of those pre-existing closure edges would balloon
  this critical bugfix's scope far beyond its actual diff; the fix itself only touches
  _land.py/_reporting.py plus its own two test files and one doc anchor, all of which
  are in scope.
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: T-4287 AC3 requires reopen_ticket() to name live worktrees it will strand
    before performing the DONE->QUEUED transition; that verb lives in _reporting.py,
    not _land.py -- widening scope per the ticket's own instruction to widen rather
    than drop AC3.
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: T-4287 AC3 requires reopen_ticket() to name live worktrees it will strand
    before performing the DONE->QUEUED transition; that verb lives in _reporting.py,
    not _land.py -- widening scope per the ticket's own instruction to widen rather
    than drop AC3.
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_land_sibling_regression.py
  reason: 'T-4287: bound test evidence lives in these two test files (SCOPE001), and
    reopen_ticket''s AC3 behavior needed a docs/modules/tickets.md#public-api touch
    to satisfy AFFECT001.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_reopen_ticket.py
  reason: 'T-4287: bound test evidence lives in these two test files (SCOPE001), and
    reopen_ticket''s AC3 behavior needed a docs/modules/tickets.md#public-api touch
    to satisfy AFFECT001.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-4287: bound test evidence lives in these two test files (SCOPE001), and
    reopen_ticket''s AC3 behavior needed a docs/modules/tickets.md#public-api touch
    to satisfy AFFECT001.'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
acceptance:
- text: given a ticket reopened through the audited verb, when a worktree that forked
    while it was terminal lands, then the land proceeds rather than being refused
    as a regression
  evidence: []
- text: given a terminal ticket resurrected by a hand-resolved merge conflict rather
    than by the reopen verb, when a land splices it, then the refusal still fires
    exactly as it does today
  evidence: []
- text: given live worktrees that would be affected, when a reopen is about to be
    performed, then they are named before the transition rather than discovered afterwards
    by a blocked land
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REOPENING A TERMINAL TICKET POISONS EVERY WORKTREE THAT FORKED BEFORE IT, AND THE
AUDITED ESCAPE HATCH HAS NO ESCAPE. Measured today, at a cost of two completed
tickets stranded and unable to land.

WHAT HAPPENED. A ticket was found to be falsely closed: its state was terminal
while none of its code had reached the integration branch. That is precisely the
situation the reopen verb documents itself as existing for -- it accepts only a
terminal starting state and describes itself as the audited escape hatch for a
falsely-closed ticket. So it was reopened, with the measurement recorded in the
reason.

Immediately afterwards, two unrelated tickets that were finished, tested and
closed could not land. Both failed deterministically, three attempts each, with
the terminal-state-regression refusal naming the reopened ticket. Neither
refusal had anything to do with the diffs being landed.

THE MECHANISM. The land-time guard refuses when a ticket that was terminal before
this land's splice is neither terminal nor archived afterwards. It exists to catch
a hand-resolved merge conflict resurrecting a closed ticket, which is a real
incident this project has already suffered. But it cannot distinguish that
accident from a DELIBERATE, audited reopen performed through the verb built for
it. Every worktree that forked while the ticket was terminal now carries a ledger
in which it is terminal, and every land from those worktrees looks exactly like
the accident.

WHY THIS IS WORSE THAN A NORMAL CONFLICT. There is no forward move available to
the blocked party. The worktrees cannot fix it -- the state they would have to
change belongs to someone else's ticket. The rule against hand-editing the ledger
is correct and both agents obeyed it, which left them with nothing to do but
report. And the number of poisoned worktrees grows with how long the ticket stays
non-terminal, so the blast radius is a function of how quickly someone happens to
notice.

WHAT A FIX MUST PRESERVE. The guard's actual purpose. An accidental resurrection
through a merge must still be refused; that incident was expensive and the
protection is worth keeping. What must change is that a transition performed by
the reopen verb is recognisable as deliberate. The reopen already records an
actor, a timestamp and a required reason, so the information needed to tell the
two apart is present -- the guard simply does not consult it.

CONSIDER ALSO WHETHER REOPEN SHOULD WARN AT THE POINT OF USE. Whoever reopens a
ticket is usually the person best placed to judge the cost, and today that person
had no idea the verb would strand two finished tickets. Naming the live worktrees
that will be affected, before performing the transition, would turn a surprise
into a decision.

DO NOT FIX THIS BY WEAKENING THE GUARD TO IGNORE NON-TERMINAL OUTCOMES
GENERALLY. That would restore the exact resurrection incident it was written for.
The distinction to encode is deliberate-and-audited versus accidental, not
terminal versus non-terminal.
