---
id: T-2291
title: reconcile --apply writes ledger demotions before its LandInProgress guard refuses,
  stranding them uncommitted and DirtyMain-blocking every agent land
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_reconcile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a land in progress, when frob ticket reconcile --apply runs and refuses,
    then no ticket.md has been modified and git status on the root is clean
  evidence: []
- text: given no land in progress, when reconcile --apply runs, then it requeues and
    commits as before (behaviour preserved)
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17, reproduced as a real incident on main.

`frob ticket reconcile --apply` mutates ledger files BEFORE its
LandInProgress guard can refuse, then abandons those mutations
uncommitted in the shared root.

CODE PATH: `src/frob/tickets/_reconcile.py:244` calls
`_requeue_stale_holds(root, stale_ids) if apply else stale_ids`, which
writes `state: in-progress -> queued` into each ticket.md. The T-1936
auto-commit of those rows happens LATER, and that is where the
"a `frob ticket land` process is running against this repository" refusal
fires. Result: files written, commit refused, changes stranded.

OBSERVED INCIDENT (timeline from git log):
  13:24  T-2276 start transition (agent begins work)
  ~13:3x reconcile --apply writes demotions for T-1382, T-1662, T-2276,
         then refuses with LandInProgress and exits non-zero
  13:36  an unrelated implementer agent finds the dirty root, is
         DirtyMain-BLOCKED from landing its own ticket, and commits the
         residue by hand as "reconcile stale in-progress state after
         orphaned lock reclaim" (9246d4b5a)
  13:41  same agent discovers T-2276 was demoted mid-land and restores it
         (2d854269c)
  13:45  T-2276 finally lands

So a refused command silently handed its cleanup to a random agent, cost
that agent a blocked land plus two recovery commits, and left the ledger
in a state nobody chose. A later `reconcile --apply` then reported
"no stale in-progress holds found" -- TRUE, but only because the
abandoned writes were already sitting in the working tree. The success
report was reading the residue of the failed run.

FIX DIRECTION: check LandInProgress BEFORE any write (the guard is cheap
-- it is a lock read plus a process scan, and it already runs in ~7ms on
the fast path), or make the whole apply atomic so a refusal rolls the
ledger back. A command that cannot commit must not write.

POSITIVE CONTROL: a test that starts a land, runs `reconcile --apply`
concurrently, and asserts the shared root is CLEAN afterwards -- not
merely that the command exited non-zero. Exit status is not the artifact.
