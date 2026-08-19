---
id: T-2671
title: 'rapid-debt DirtyMain recurs after T-2669 under concurrent root writes: a second,
  intermittent cause'
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
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
## Measured

T-2669 landed at 16:28:54 and fixed one cause of the rapid-debt DirtyMain
failure (`_commit_rapid_debt` not setting `FROB_LAND_INTERNAL=1`, so the
T-2071 pre-commit hook refused it). That fix is real and self-confirmed on
its own land.

It is NOT the only cause. On current main:

    546ddf39c  16:36:59  chore: commit rapid-debt.jsonl (land-side commit failed)

That is T-2619's land, EIGHT MINUTES AFTER T-2669 landed. And the fix was
present in the tree that land ran from -- verified:

    git show aab3dc95c:src/frob/app/ticket_runner/_rapid_sweep.py
      | grep -c _land_internal_git_env
    -> 2

So this is a second, distinct failure mode, not a stale-worktree miss and
not a regression of T-2669.

(Coordinator note: I initially misdiagnosed this as a pre-fix worktree. I
had checked the worktree's pre-merge HEAD; the correct check is the tree the
land actually ran from, since the land merges main before running. The
agent's evidence was better than mine.)

## Leading hypothesis -- verify, do not assume

Concurrent-write contention on the shared root. At the moment of failure:
- `fleet_status` reported 2 lands in flight
- `chore(tickets): mirror scope T-2666 from worktree` landed at 16:36:51,
  22 seconds before the failure and inside the same window

Two processes writing the shared root at the same moment is a different
mechanism from a hook refusing a single commit, and T-2669's fix was never
meant to cover it.

The blocker to confirming this is evidence, not analysis: the actual land
invocation's own log was not available. Only the detached post-land sweep
log survives, and it is silent on the failure. So the FIRST task here is
making the failure observable -- capture and retain the land's own stderr
for this step, so the next occurrence names its own cause instead of
requiring reconstruction from commit timestamps.

Do that before designing a fix. A concurrency fix built on an unconfirmed
hypothesis is how this repo got two mechanisms for one problem before.

## Why it still matters after T-2669

The DirtyMain consequence is unchanged: a failed commit of the land's own
machinery file leaves the shared root dirty, and that makes `frob ticket
land` refuse for EVERY other agent until someone commits by hand. T-2669
removed the deterministic cause; this is the remaining intermittent one, and
intermittent is worse to diagnose.

Measured frequency before T-2669: 70 hand-commits in one day. After: at
least one confirmed. Re-measure over a window with the fix live rather than
assuming the rate is now near-zero.

## Do NOT

- Do NOT revert or weaken T-2669. It fixed a real, separately-confirmed
  cause and its own land proved it.
- Do NOT serialise all land-adjacent writes as a first move. That trades an
  intermittent dirty root for a throughput ceiling, and land concurrency is
  already this fleet's binding constraint.
- Do NOT make the sweep skip writing the file. It is the deferred-
  verification debt ledger; dropping it is a silent zero.

## Positive controls, both directions

- reproduce the failure deliberately under concurrency (two lands, or a
  land plus a ledger-mirror write, contending on the shared root) BEFORE
  fixing -- if you cannot reproduce it, say so rather than fixing blind
- after the fix, that same reproduction leaves the root CLEAN
- a single uncontended rapid land still commits its own rapid-debt line,
  i.e. T-2669's behaviour is preserved
- the DirtyMain guard still fires for genuinely unexpected root content --
  an untracked file, or an edit to a source file the land does not own
