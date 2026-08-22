---
id: T-2840
title: frob ticket requeue from a worktree reports success while its ledger mirror
  never reaches main, leaving a stale in-progress state and a held lease
state: in-progress
kind: bug
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_ledger_mirror.py
- tests/unit/test_ticket_runner_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: requeue reclassify fix needs coverage in this repo's existing ledger-mirror
    test module
  actor: logan
  at: '2026-08-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured 2026-08-21

An agent ran `frob ticket requeue T-2370` from inside a worktree. The command
reported SUCCESS. Its ledger-mirror commit never reached main.

Main was left reading `state: in-progress` after a "successful" requeue. The
agent caught it only by reading `tickets/T-2370/ticket.md` on main
post-hoc, then reapplied the requeue from the primary checkout (`4890d9d2a`),
which worked.

Suspected mechanism, to be confirmed rather than assumed: the worktree was
empty / had no declared scope, and such worktrees appear to be cleaned up
eagerly -- so the worktree vanished before its mirror commit propagated. The
agent observed the timing but did not instrument it.

## Why this matters

Ticket state on main is what every other agent and the coordinator reads to
make dispatch and lease decisions. A requeue that reports success while main
still says `in-progress` leaves:

- a LEASE still held on main, blocking other agents from the file set
- a ticket that looks actively worked when nobody is working it
- a coordinator (me) making decisions from a state that the tool already
  told someone was changed

I hit the downstream consequence of exactly this class earlier the same day:
two tickets held leases with no worktree, invisible until `fleet_status`
flagged them LEAK, and one of them blocked another agent's last REG008 entry
for hours.

## This is a known class, not a novel bug

T-2785 fixed the same shape for `set-parent`: the setter wrote to disk,
reported success, and its auto-commit was refused by a concurrent land --
leaving the shared root dirty while telling the caller it worked. The fix
added `_refuse_write_if_land_in_progress` so a refusal leaves the tree
untouched rather than stranding a partial write.

`requeue` appears to have an analogous gap on the MIRROR path rather than the
commit path. Check whether T-2785's guard covers `requeue` at all, and
whether the mirror step has any success/failure reporting distinct from the
local write.

## Required shape

A ledger mutation must not report success unless the state it claims to have
changed is actually durable where readers will look for it. Either:
- verify the mirror reached the primary checkout before reporting success, or
- report explicitly that the change is LOCAL-ONLY and name the follow-up
  needed.
Silent partial success is the worst of the three options, and it is what
happens today.

Consider also whether an empty/no-scope worktree should be eligible for eager
cleanup at all while it holds uncommitted ledger mirror state.

## Positive controls, both directions

- A requeue issued from a worktree that is then removed: main MUST end up
  with the requeued state, or the command must FAIL loudly. Plant this by
  requeuing from a scopeless worktree and removing it immediately.
- A requeue issued from the primary checkout still works exactly as today.
  Without this control the fix is indistinguishable from breaking requeue.
- A requeue whose mirror genuinely cannot propagate reports a clear typed
  error rather than exit 0.

## Verification note

Do NOT verify this by reading the worktree's own copy of the ticket -- that
is the copy that looked correct while main was wrong. Read
`tickets/T-<id>/ticket.md` on MAIN, or `git -C <root> show main:tickets/...`.
