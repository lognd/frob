---
id: T-1984
title: 'block writes a permanent edge for a transient lease collision, and there is
  no unblock: two starved tickets are now unreachable'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket block <id> --by <other>` writes a permanent `blocked_by`
graph edge. There is no inverse verb -- `frob ticket --help`'s subcommand
list has no `unblock`/`unlink`/`clear`, and `block --help` offers only
`--by`. The edge can only disappear when the blocker reaches a terminal
state.

That is the wrong lifetime for the most common reason a block gets
written: a TRANSIENT scope-lease collision.

MEASURED, 2026-08-10:
- An agent found T-1638 and T-1748 (both need `src/frob/tickets/_land.py`)
  colliding with T-1696's live lease on that file. Following the playbook,
  it recorded `frob ticket block T-1638 --by T-1696` and the same for
  T-1748, rather than forcing past the lease. Correct behavior.
- T-1696 turned out to be a multi-session ticket (a ~8300-line collapse
  across `_land.py`/`_land_cmd.py`). Its agent completed only the seam
  enumeration and edited nothing.
- I therefore narrowed T-1696's scope, releasing `_land.py` and
  `_land_cmd.py`. The lease collision is GONE.
- T-1638 and T-1748 are still not dispatchable: `frob ticket doable` no
  longer lists either, because `blocked_by=['T-1696']` persists and
  T-1696 will stay open for sessions.

So two tickets starved 96h and 72h respectively are now unreachable
because of a condition that no longer exists, and nothing in the CLI can
undo it. `frob ticket requeue` refuses ("queued, not in-progress"), and
hand-editing the ledger is forbidden here for good reason.

THE REAL DEFECT is not the missing verb -- it is using a PERMANENT graph
edge to record a TRANSIENT condition. The lease system already tracks
scope collisions dynamically and correctly: `frob ticket doable` filters
on live leases (T-0453) and `ticket start` refuses on collision. A
lease-collision block therefore duplicates a mechanism that already
self-heals, in a form that cannot.

DO NOT FIX IT THIS WAY:
- Do NOT just add an `unblock` verb and stop. It would fix this instance
  while leaving the same trap for the next agent, and per the standing
  directive a command requires knowing the command -- the agent that
  writes the block is following the playbook and has no reason to think
  it needs undoing later.
- Do NOT auto-clear `blocked_by` edges generally. Most blocks encode real
  dependency (T-1552 blocked by T-1971 is a genuine precondition) and
  silently dropping those would let unpreconditioned work be dispatched.
  Only the lease-collision kind is transient.
- Do NOT tell agents to stop recording lease collisions. Recording them
  is better than forcing past a lease.

FIX DIRECTION, preferred order:
(a) Do not record a lease collision as a `blocked_by` edge at all. The
    playbook should have the agent report and move on; the lease system
    already keeps the ticket out of `doable` while the collision is live,
    and lets it back in automatically when the lease frees.
(b) If a durable record is wanted, make it a DISTINCT, self-expiring kind
    of edge that is re-evaluated against live leases rather than against
    the blocker's terminal state.
(c) An `unblock` verb as the manual escape hatch for a block written in
    error -- useful, but not sufficient on its own.

ACCEPTANCE: first test must FAIL before the fix -- record a lease-collision
block, release the lease, and assert the blocked ticket returns to
`frob ticket doable`. Then assert a genuine dependency block (a real
precondition, not a lease collision) is NOT cleared by the same path.
Also unblock T-1638 and T-1748 as part of this work, and confirm both
reappear in the doable set.
