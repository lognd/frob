---
id: T-1909
title: A dropped ticket's scope lease survives in a stale worktree's local ledger
  and blocks unrelated work indefinitely
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_doable.py
- tests/test_ticket_leases.py
- tests/test_ticket_leases_cross_worktree.py
- tests/test_tickets_leases.py
- src/frob/tickets/_new_renumber.py
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: the lease read/staleness layer T-1909 targets
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: the lease read/staleness layer T-1909 targets
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_leases.py
  reason: existing lease test suites, closes the scope-closure warnings
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: existing lease test suites, closes the scope-closure warnings
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_tickets_leases.py
  reason: existing lease test suites, closes the scope-closure warnings
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-1891: the internal batching callers whose spurious no-commit warning
    this ticket fixes'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-1891: the internal batching callers whose spurious no-commit warning
    this ticket fixes'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease::test_dropped_ticket_on_local_ledger_does_not_block_live_lease
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator. T-1893 (docs, scope=docs/modules/gates.md) could not be started: ScopeLeaseConflict reported the file as leased by in-progress T-1579.

But T-1579 had been DROPPED on main earlier the same day. The stale lease was coming from a different worktree (.claude/worktrees/t-1579) whose LOCAL ticket ledger still read 'state: in-progress' -- that worktree branched before the drop and was never refreshed or removed. The agent correctly refused to force through the collision and reported it; the block cleared only when I removed the stale worktree by hand.

WHY IT MATTERS. Lease state is authoritative for dispatch, and this makes it unfalsifiable from the consumer's side: the blocked agent sees a live in-progress lease and has no way to learn the holding ticket is terminal on main. The work stalls silently until a human notices. It also scales the wrong way -- a long parallel drive accumulates worktrees, and every abandoned one is a permanent lien on whatever files its ticket declared. This session ended with 13 stale worktrees, any of which could have held a lease of this kind.

Note the interaction with the standing worktree-per-agent workflow: worktrees are created constantly and removed only when someone remembers. The leak is therefore the DEFAULT outcome, not an edge case.

FIX (decide on merit):
1. Resolve lease holders against the ledger state on MAIN, not the holder worktree's local copy -- a lease whose ticket is done/dropped on main is not a lease.
2. And/or have the drop/close path actively release leases the ticket holds, wherever its worktree happens to be.
3. And/or treat a lease whose worktree no longer exists (or whose branch is merged/terminal) as dead, with a clear diagnostic naming the stale worktree so the operator can act.
Whichever is chosen, the ERROR MESSAGE must name the holding worktree path and the holder's state on main -- the current message says only 'leased by in-progress T-1579', which is actively misleading when T-1579 is dropped.

Add a regression test: a lease held by a worktree whose ticket is dropped on main must NOT block a new start.

Related: T-1883 (same-worktree false blockers), T-1880 (lease grant-time collision), and the epic-lease-leak pattern already recorded for T-1686.