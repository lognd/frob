---
id: T-1981
title: 'Burn down SYS110_UNAUDITED_NODES: T-1629''s rule enforces on 2 of 17 nodes
  until the 15 exempted mirrors are hand-audited'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_selfconform.py
- design/frob.strata
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: per-node interface= audit fixes live in design/frob.strata, the design model
    file itself -- the ticket's declared scope (_selfconform.py) is where the exemption
    frozenset lives, not where the hand-declared interface= blocks being audited live
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: acceptance test for the burn-down (asserting the exemption set shrinks and
    never widens) lives in this existing test module
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_burn_down_shrinks_the_exemption_never_widens_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1629 shipped SYS110 (a node's real public surface must be a subset of
its hand-declared `interface=`), but exempted 15 of the 17 nodes that
have `interface=` blocks via `SYS110_UNAUDITED_NODES`
(`frob.strata._selfconform`). The rule therefore enforces on 2 nodes.

The exemption was correct and correctly disclosed: those 15 carry stale
T-0668-era GENERATED mirrors, measured at 734 findings of real drift, and
enabling the check unconditionally would have broken `TestRealGateGreen`.
Phasing was the right call. This ticket is the other half -- without it
the exemption is permanent and SYS110 is decorative for 88% of its
domain.

WHY THIS NEEDS ITS OWN TICKET: a hand-typed exemption frozenset inside a
source file is not tracked by any queue. T-1629 is `done` and archives;
nothing then reports that 15 nodes are unaudited, and no gate fails
while they remain. That is the catalogued-is-not-enforced shape --
compare T-1960, where 7 "wire X into Y" follow-ups sat at medium and
starved because nothing carried the pressure forward.

It is also the shape recorded from T-1967 earlier today: an exemption
that covers the normal case turns a guard off while leaving it looking
green. Here the exemption covers 15/17 of the population.

MEASURED:
- `SYS110_UNAUDITED_NODES` in `src/frob/strata/_selfconform.py`: 15 node
  ids exempted.
- Enforced today: `checker`, `fleet` only.
- Drift behind the exemption: 734 findings across the 15, per T-1629's
  own measurement.

THE WORK: audit each exempted node's `interface=` block, replace the
stale generated mirror with hand-declared INTENDED surface, and remove
that node id from the frozenset. One node per commit is fine and
probably safer; the goal is the frozenset reaching empty and being
deleted along with the code that reads it.

DO NOT FIX IT THIS WAY:
- Do NOT auto-generate the corrected `interface=` blocks. T-1870 DELETED
  the auto-measured mirror on an explicit owner directive that no code
  path may auto-update declared public-symbol surface, and T-1629's
  whole premise is that `interface=` means hand-declared INTENT.
  Regenerating the mirror would restore precisely what both tickets
  removed, while making SYS110 pass. That is the tempting shortcut and
  it inverts the point of the rule.
- Do NOT empty the frozenset without auditing, to "turn the rule on".
  That converts 734 disclosed findings into 734 gate errors on main and
  reds the floor for everyone.
- Do NOT widen the exemption to silence a node that turns out to be
  hard.

ACCEPTANCE: first test must FAIL before the fix -- assert
`SYS110_UNAUDITED_NODES` is smaller than its current 15 (and ultimately
empty). Per node removed, record the before/after finding count for that
node and confirm the unscoped floor stays at its current value. When the
frozenset reaches empty, delete it and the branch that consults it.