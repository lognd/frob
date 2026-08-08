---
id: T-1883
title: doable --show-blocked reports same-worktree leases as blockers, so a grouped
  dispatch self-blocks
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED, 2026-08-08, coordinator. Three tickets are being worked as a
group from ONE worktree (`t1552-ledger-v2`), and all three legitimately
declare `docs/modules/tickets.md` in scope:

  T-1832  scope=['docs/modules/tickets.md']
  T-1865  scope=['docs/modules/tickets.md', '.../_rapid_sweep.py']
  T-1878  scope=['docs/modules/tickets.md', '.../_scope.py']

`frob ticket doable --show-blocked` reports each of them as BLOCKED BY
THE OTHER TWO:

  T-1832  held: scope 'docs/modules/tickets.md' leased by in-progress
          T-1865 (.../worktrees/t1552-ledger-v2); scope
          'docs/modules/tickets.md' leased by in-progress T-1878
          (.../worktrees/t1552-ledger-v2)

The blocking lease and the blocked ticket are in the SAME WORKTREE. A
worktree cannot conflict with itself -- there is exactly one working
copy and one agent editing it. This is a false blocker.

WHY IT MATTERS. Dispatch policy in this repo is to give each agent a
GROUP of related tickets to amortise cold start, and related tickets
routinely share a doc. So the recommended workflow reliably produces
self-blocking groups. Worse, the false blockers pollute
`doable --show-blocked`, which is the primary instrument for choosing
what to dispatch: at the time of filing, that command reported ZERO
dispatchable tickets out of 67 queued, and an unknown fraction of that
was this artifact rather than real contention. A queue-planning tool
that overstates contention causes idle agents.

ROOT CAUSE, and this is the important part: T-1868 got this exactly
right. Its `_scope_add_live_lease_conflict` in `src/frob/tickets/_scope.py`
is explicitly a CROSS-WORKTREE check -- it compares the requesting
worktree against sibling worktrees and does not fire on itself, which is
why these three `scope --add` calls were correctly allowed. The
doable/blocked computation in `src/frob/tickets/_doable.py` performs the
same conceptual query with a DIFFERENT and wrong rule. Two code paths
answering "does this lease conflict?" with different answers is the
duplication this repo treats as a defect: the two will keep diverging.

REQUIREMENTS.

1. Exclude same-worktree leases from the blocked-by computation.
2. Do NOT fix this by copying T-1868's predicate. EXTRACT the single
   conflict predicate into one home and have both `_scope.py` and
   `_doable.py` call it. One home, not two copies -- if the answer to
   "do these two leases conflict?" can differ between call sites, the
   bug recurs under a new name.
3. The shared predicate must compare glob-EXPANDED path sets, not
   literal scope strings, matching T-1868's `scope_overlap_globs`
   behaviour. `src/frob/app/config.py` versus `src/frob/app/**` is the
   same conflict and a string compare misses it.
4. Regression test with two real `git worktree` checkouts, following
   T-1868's own test precedent: assert same-worktree leases do NOT
   block, and cross-worktree leases DO.
5. Re-run `frob ticket doable --show-blocked` before and after and
   record both counts of genuinely-dispatchable tickets in the Done
   report. The delta is the measurement that proves this fixed a real
   throughput problem rather than a cosmetic one.

NOTE ON STATE. On `main` these three tickets read `state: queued`; the
`in-progress` state is committed on the agent's own branch. So on main
the LEASE FILE is the only authority for in-flight status, and the
blocked computation reads it correctly -- that part is not the bug. The
bug is purely the missing same-worktree exclusion.
