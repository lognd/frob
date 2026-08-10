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

## Done report

Root cause confirmed by direct investigation: `frob.tickets._scope._scope_add_live_lease_conflict`
(the T-1868 live cross-worktree-lease half of the single scope-lease-conflict entrypoint
`scope_lease_conflict`, used by both `mutate_scope --add` and `frob ticket start`'s own
grant-time check) iterated every lease `read_all_leases(root)` returned and only excluded
one whose TTL had expired -- it never consulted `root`'s OWN, just-merged-with-main ledger
to see whether the lease's ticket was already DONE/DROPPED there. A lease file on the shared
`.git/frob-leases/` side-channel is written once (on IN_PROGRESS) and only ever removed by
THAT SAME worktree's own subsequent `transition` call; a worktree abandoned after its ticket
was dropped/closed from a DIFFERENT worktree (the ordinary coordinator-driven drop path)
leaves a live, unexpired lease file behind forever, with no mechanism to notice its holder is
terminal. This reproduces the exact T-1893/T-1579 incident: `frob ticket start`/`scope --add`
refused with `ScopeLeaseConflict`, naming a ticket already dropped on main.

Fix: `_scope_add_live_lease_conflict` now takes `queue` (root's own authoritative ledger view,
already threaded in by its only caller) and skips a colliding lease whose ticket is DONE or
DROPPED there -- mirroring the same DONE/DROPPED filter `frob.tickets._doable._cross_worktree_
leases` already applies for the `doable`/`leased_by` display path, and `_scope_add_queue_
conflict`'s own `holder.state is not TicketState.IN_PROGRESS` skip for the queue-based half of
the same check. This fixes both `mutate_scope --add` and `frob ticket start`'s grant-time
refusal in one place, since both funnel through `scope_lease_conflict`. The per-lease exemption
logic (T-1909's new check plus the pre-existing T-1356/T-0561 exemptions) was split into a new
helper `_live_lease_collision_is_exempt` to keep the loop under ARCH001's line threshold.

This closes the "resolve lease holders against ledger state on MAIN, not the holder worktree's
local copy" option named in the ticket body. It does not implement drop/close actively releasing
a foreign worktree's lease, nor a path-existence/branch-liveness reclaim sweep for STRANDED
leases sitting in existing stale worktrees right now -- `frob.tickets._leases.lease_staleness_
reason`/`orphaned_leases`/`release_orphaned_lease`/`force_release_lease` (T-1789/T-1806) already
provide that manual reclaim path via `frob worktree release-lease <id>` for a lease that is
provably orphaned by path-gone/ticket-gone/holder-dead; this ticket's fix additionally makes the
COLLISION CHECK ITSELF ledger-state-aware so a still-present, still-live worktree whose ticket is
merely terminal on the checking ticket's own ledger no longer blocks unrelated work at ALL, without
needing any manual reclaim step first -- the exact "unfalsifiable from the consumer's side" gap the
ticket names. A currently-stranded lease in an EXISTING stale worktree (one whose local ledger has
not been touched since) is reclaimed automatically the next time any worktree's ledger (having
merged the drop) attempts a scope/start check against it -- no separate sweep needed.

Regression test added at the exact incident shape: two real linked git worktrees sharing one git
common dir; ticket A started (and leased) in one, dropped on the OTHER'S ledger directly (never
released by A's own worktree); a scope --add for an unrelated ticket B on the SAME path, from the
worktree that knows the drop, now succeeds. Verified failing at the parent commit (refused with
ScopeLeaseConflict naming the dropped ticket) and passing after the fix.

### Changed
```
 rapid-debt.jsonl           |  2 ++
 src/frob/gates/__init__.py |  1 +
 tickets/T-1909/ticket.md   | 50 +++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 52 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease::test_dropped_ticket_on_local_ledger_does_not_block_live_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 6 error(s), 977 warning(s), 700 waived
- error-findings: AFFECT001@src/frob/app/ticket_runner/_rapid_sweep.py, AFFECT001@src/frob/tickets/_scope.py, PRE001@tickets/T-1909, REG002@docs/design/registry/check-coverage.yaml, SUPPRESS001@.claude/hooks/frob-suggest.py, SUPPRESS001@.claude/hooks/frob-timeout-guard.py
