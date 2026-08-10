---
id: T-1748
title: Two tickets sharing one fix mechanism cannot land from one worktree without
  disabling PassengerTickets and BUG002
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_mutation_evidence.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Two tickets that share one fix mechanism cannot both be landed cleanly
from one worktree. Both agents who hit it today reached for a different
workaround, and neither is what the tool should require.

The shape: an agent is given two related tickets (correctly -- they share
a mechanism, so one agent holding both avoids a lease fight and avoids
two people building the same primitive). It implements the shared piece,
lands ticket A, and then ticket B's land refuses, because:

- `PassengerTickets` scans the WHOLE BRANCH DIFF for `frob:ticket <id>`
  additions, not the per-ticket diff. B's branch still carries A's
  commits, so A rides along as an undisclosed passenger -- and
  symmetrically, landing B first makes A the passenger. There is no
  order that avoids it.
- BUG002 then refuses B on its own terms: B's designated repro
  necessarily ALREADY PASSES at main, because A's land carried the shared
  code. The repro cannot fail-at-parent when the parent already contains
  the fix.

Observed twice on 2026-08-07, with two different escapes:

1. One agent isolated ticket A's commits into a FRESH worktree
   (`git worktree add` at a specific sha), landed A independently, then
   merged B's backup branch onto the post-land state and landed B. Manual,
   fiddly, and it invented a worktree the lease model knows nothing about.
2. The other used `--allow-cross-ticket` on BOTH lands plus a
   `frob:waive BUG002` on the second. Each override is individually
   documented and justified, but the combination means two tickets landed
   with the passenger check and the repro check both disabled -- which is
   most of what those gates exist for.

Neither agent did anything wrong. The tool made them choose between
tedium and turning off the checks.

The second agent judged this "not reproducible as a general defect,
happened inside my own worktree". It is general: it follows mechanically
from stacked commits on one branch plus a whole-branch passenger scan,
and it will recur every time a coordinator groups related tickets --
which is the dispatch strategy this drive uses deliberately, because
ungrouped related tickets fight over leases instead.

WANTED:

1. `PassengerTickets` should evaluate the diff attributable to THE
   TICKET BEING LANDED against main, not the whole branch diff. A commit
   already landed on main is not a passenger; that is exactly what
   "already on main" means. Check reachability rather than scanning the
   branch's accumulated text.
2. BUG002's repro check needs a defined answer for "the fix reached main
   via a sibling ticket in this same series". Passing at parent is
   correct here and not evidence of a bad repro. Either detect the
   sibling-land case explicitly, or make `frob:no-behavior-change`'s
   sibling analogue the documented disposition -- but do not leave
   `frob:waive BUG002` as the only route, because a waiver records
   "we decided to skip this" when the truth is "this check is not
   applicable in this configuration". Those are different facts and the
   ledger should not conflate them.
3. Whatever the fix, `frob ticket land` should be able to land a series
   of related tickets from ONE worktree in dependency order without
   overrides. That is the normal case for grouped dispatch, not an edge
   case.

Evidence must include the real shape: two tickets sharing a mechanism,
stacked on one branch, landed in order, with no `--allow-cross-ticket`
and no BUG002 waiver.