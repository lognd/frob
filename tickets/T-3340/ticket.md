---
id: T-3340
title: close should not mirror state/evidence onto main until land publishes them
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner/*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3288 (frob ticket land --finish DELETED a worktree
without merging).

T-3288 fixes the SHORTCUT's own premise (it now confirms the ticket's scope
content is actually present on main via _worktree_content_already_on_main,
not just a terminal ledger state) and adds a backstop in _finish_worktree
(REQUIRED verified_landed kwarg, no bypass) that refuses to remove a worktree
whose content is not confirmed landed. Both fixes are guard-the-edge fixes.

The WINDOW itself is still open: frob ticket close inside a worktree mirrors
state/evidence onto main immediately (F-033), while the actual code stays on
the branch until frob ticket land runs. Between close and land, main
legitimately reads state: done with N evidence ids for a ticket whose code is
nowhere on main. This window is the false premise that produced the F-034
incident in the first place.

PROPOSED DIRECTION: close should mirror ONLY scope/lease onto main, and leave
state/evidence on the BRANCH until land itself publishes them onto main as
part of the same commit that carries the code. This removes the window
rather than guarding its edge.

RELATED: T-3336 (frob ticket close reports success then land refuses as
NotCloseable) is a second, independently-discovered instance of close and
land disagreeing about what done means. Be consistent with T-3336's own
conclusion once it lands.

OUT OF T-3288's SCOPE: T-3288's own declared scope is
src/frob/app/ticket_runner/_land_cmd.py only; the close-side mirroring code
lives elsewhere, so this is filed as its own ticket.