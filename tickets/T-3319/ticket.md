---
id: T-3319
title: 'Worktree land ownership: dry-run misses lease conflict, work --steal exits
  1 despite success'
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
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-013).

Flow: `frob ticket start T-0001` run in the MAIN checkout (not a worktree),
then branch + commit there, then `git worktree add ../wt/T-0001 <branch>`
and `frob ticket land T-0001 --worktree ...`. `land --dry-run` passes clean.
The REAL land merges, then fails with TicketOwnershipViolation because the
scope/tree lease is still held by the main checkout, not the worktree.
Nothing in `--dry-run` predicted this. The suggested recovery, `frob ticket
work --steal`, DOES transfer the lease successfully but then itself exits 1
("already in-progress -- run sweep instead") even though the steal already
succeeded -- the retry land then works, so the failure is purely cosmetic/
misleading, not a real block, but it reads as one.

THREE FIXES REQUESTED, evaluate and build what is right:
  (a) `land --dry-run` should check lease ownership and predict this
      TicketOwnershipViolation instead of passing clean.
  (b) `frob ticket work --steal` on an in-progress ticket, when the steal
      itself succeeds, should be a clean SUCCESS (exit 0) -- not exit 1 with
      a message that contradicts what it just did.
  (c) `frob ticket start` run in the PRIMARY checkout (not a worktree) on a
      ticket that will later need `land --worktree` could warn at START time
      that this sequence will need a lease transfer before land.

WHAT NOT TO DO: do not silently auto-transfer the lease at land time without
telling the user -- ownership transfer is exactly the kind of thing this
repo's own incident history (T-1848-family writeups) says must be visible,
not implicit.

MUST-FIRE FIXTURE: start-in-main then land-from-worktree without a steal --
`land --dry-run` must now report the ownership problem BEFORE the real land
attempts and fails.

MUST-STAY-QUIET FIXTURE: the ordinary `frob ticket work T-X` (worktree-first)
flow -- no new warnings, `--dry-run` and steal behave exactly as before.
