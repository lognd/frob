---
id: T-4684
title: cross-worktree lease release must not gate on the LOCAL ticket's prior state
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- tests/test_ticket_leases_cross_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_drop_from_a_worktree_that_never_saw_in_progress_still_releases
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_release_on_close_removes_the_lease
designated_repro_test: tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_drop_from_a_worktree_that_never_saw_in_progress_still_releases
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-19 while working T-4659 (repro script kept in the T-4659
worktree's why-file): `frob.tickets._evidence._sync_cross_worktree_lease`
gates `release_lease` purely on the LOCAL `Ticket.state` transition
(`from_state is TicketState.IN_PROGRESS`), never on whether a
cross-worktree lease FILE actually exists for the ticket id under
`.git/frob-leases/`.

Repro: a ticket is filed and PLANNED on `main`'s own branch/checkout and
that commit lands. A second worktree of the SAME repo (own branch, own
uncommitted-to-main history) starts the ticket (`IN_PROGRESS`) and
records the cross-worktree lease -- `main`'s own local ledger view never
observes this transition (tickets.md is per-branch). A coordinator then
runs `frob ticket drop <id>` FROM `main`: `main`'s local `ticket.state`
was PLANNED (not IN_PROGRESS), so `_sync_cross_worktree_lease`'s
`elif from_state is TicketState.IN_PROGRESS` branch never fires and
`release_lease` is never called -- the transition to DROPPED succeeds,
but the cross-worktree lease file survives, exactly the shape measured
live as the T-3259 incident (`frob ticket drop T-3259` left
`.git/frob-leases/T-3259.json` in place, later cleared by hand with
`frob worktree release-lease`).

Fix belongs in `frob.tickets._evidence._sync_cross_worktree_lease`
(T-4659's own scope is `_leases.py`/its own new test file/its own doc --
this call site is out of that scope): on ANY transition INTO a terminal
state (DONE/DROPPED) or out of IN_PROGRESS by the state machine's own
`_TRANSITIONS` table, call `release_lease` unconditionally (it is already
idempotent -- a no-op `Ok(None)` when no lease file exists), rather than
gating the call on the LOCAL ticket's own prior state. The cross-worktree
lease's existence, not the local ledger's view of `from_state`, is the
fact that matters.

scope: src/frob/tickets/_evidence.py, tests/test_ticket_leases_cross_worktree.py
blocked_by: T-4659