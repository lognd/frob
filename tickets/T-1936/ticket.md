---
id: T-1936
title: frob ticket reconcile --apply leaves the ledger dirty and silently DirtyMain-blocks
  every concurrent land
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_reconcile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
OBSERVED LIVE 2026-08-09. I ran `frob ticket reconcile --apply` on main
to requeue a stale in-progress hold. It correctly requeued T-1901 and
printed:

    reconcile: requeued 1 stale in-progress hold(s): [T-1901]

It then left `tickets/T-1901/ticket.md` MODIFIED AND UNCOMMITTED, with no
warning. I only noticed minutes later, by chance, running `git status`
for an unrelated reason. In that window every concurrent `frob ticket
land` in the repo was DirtyMain-blocked -- with five agents live, that is
the single most disruptive state this repo has.

THE INCONSISTENCY, measured:
- Every other ledger-mutating verb auto-commits and takes `--no-commit`
  to opt out. docs/guides/agentic-workflow.md states this as the rule.
- `frob ticket reconcile --help` shows only `--apply`, `--remove-orphans`,
  `--path`. There is NO `--no-commit`, and it does not auto-commit.
So it is the one ledger-mutating verb that neither commits nor lets you
ask it to, and it is silent about the state it leaves behind.

WORSE THAN T-1891. T-1891 (done) was about `frob ticket new` printing a
DirtyMain warning when it HAD committed -- a false alarm. This is the
mirror image and strictly more harmful: a real dirty ledger with NO
alarm. T-1891 s fix added the `warn_if_dirty` seam
(src/frob/tickets/_leases.py, `commit_ticket_ledger_change`); reconcile
appears never to have been wired through it.

WHY THIS IS NOT "the operator should remember to commit". The whole point
of reconcile is recovering from a crashed/abandoned agent -- it is run
precisely when the repo is already in a confusing state, by someone
trying to make it consistent. A recovery tool that leaves a new,
invisible, land-blocking inconsistency behind is working against its own
purpose. It should need no knowledge to use safely.

FIX: route reconcile s ledger writes through the same
`commit_ticket_ledger_change` path every other mutating verb uses, so it
auto-commits by default and accepts `--no-commit` for symmetry. Do not
fix this by only adding a warning -- a warning still requires the
operator to know what to do next, and the correct action (commit the
ledger change reconcile just made) is unambiguous and mechanical.

DO NOT make `--apply` commit anything OTHER than the ledger rows it
actually changed. It must never sweep unrelated working-tree state into
its commit; several agents may have uncommitted work in the root at the
time. Commit by explicit path, the way `frob ticket new` does.

ACCEPTANCE
1. `frob ticket reconcile --apply` leaves `git status --porcelain` clean
   for the ledger rows it changed. A test must FAIL before the fix.
2. `--no-commit` exists and leaves the change uncommitted, WITH the same
   loud DirtyMain warning `frob ticket new --no-commit` emits.
3. It commits only the paths it modified; a test proves an unrelated
   dirty file in the tree is NOT swept into its commit.
4. `--remove-orphans` is covered by the same guarantees.