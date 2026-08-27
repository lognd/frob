---
id: T-3128
title: fleet_status reports a live registered worktree as a leaked lease
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the verified false LEAK against a live registered worktree and the
    cleanup blast radius
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3168
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27, during a deliberate fleet quiesce.

`scripts/fleet_status.py` reported:

    LEASES 4 (2 live, 2 leaked, 0 blocked-open)
      T-3113 -> series-br  [live]
      T-3121 -> t-3121     [live]
      T-2992 -> <no worktree>  [LEAK]
      T-3122 -> <no worktree>  [LEAK]

T-3122's worktree EXISTS. Verified three ways:
  - `ls -d /home/logan/projects/frob/.claude/worktrees/t-3122` resolves.
  - `git worktree list` contains
    `/home/logan/projects/frob/.claude/worktrees/t-3122  78531ecad [t-3122]`.
  - The agent holding it reported live committed work there (`391a17594`) and
    was actively using it at the moment of the report.

So the leak detection produced a FALSE POSITIVE against a live, registered,
in-use worktree. Note T-3121 -> `t-3121` resolves correctly and has the same
naming shape, so this is not simply "cannot see `.claude/worktrees/`" -- the
mapping succeeds for some leases and fails for others. Find out which
discriminator is wrong before fixing; a plausible-looking fix to the wrong
predicate would leave the real bug in place.

WHY THIS IS DANGEROUS RATHER THAN COSMETIC. A leaked lease is the signal for
CLEANUP. This repo's own recorded guidance is that a sweep marks exactly the
leaked set as removable, and agent worktrees routinely hold COMMITTED work that
has not yet landed -- that is the normal steady state between commit and land.
A false leak therefore points cleanup at a live worktree containing the only
copy of unlanded work. The failure is silent and unrecoverable in the way that
matters: the branch is deleted, and nobody knows what was in it.

It is also the THIRD measurement-integrity defect found in this one file today:
  - T-3072/T-3093: `_FROB_CHECK_TOKEN_RE` never matched `python -m frob check`,
    so live-parented forkservers were reported ORPHANED (I relayed that false
    alarm to the owner several times before it was diagnosed).
  - T-3093: the LAND LOCK line reported fd-open WAITERS under a "holder" label.
  - This ticket: live worktrees reported as leaked leases.
That is a pattern in `fleet_status.py` specifically: it is the first thing
consulted when the fleet looks wrong, and its individual signals have not been
verified against ground truth. Consider whether this file needs a
ground-truth-fixture suite of its own rather than a third point fix.

ALSO CHECK: whether T-2992's LEAK is real. It may be genuine (in-progress with
no worktree is a real condition) -- but after this finding, do not assume it.
Report the verdict either way.

ACCEPTANCE
- A lease whose worktree exists and is registered in `git worktree list` is
  never reported as leaked. Must-stay-quiet fixture using a REAL registered
  worktree, not a mocked path.
- A genuinely leased-but-worktree-less ticket is still reported as leaked.
  Must-fire fixture -- do not solve this by never reporting leaks.
- The discriminator that made T-3121 resolve and T-3122 not is identified and
  named in the Done report.
- The T-2992 verdict is reported.
- State whether any cleanup path (sweep, prune, `--finish`) consumes this leak
  signal today. If one does, that is the blast radius and it must be said out
  loud.
