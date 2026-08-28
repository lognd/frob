---
id: T-3216
title: DirtyMain reports an unreadable git status as uncommitted work and tells the
  reader not to retry
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
MEASURED 2026-08-28 landing T-3191. The DirtyMain guard refused a land, naming
uncommitted work that did not exist:

    ERROR: land: T-3191 refused -- /home/logan/projects/frob has uncommitted work
    belonging to NO open ticket's scope: (git status unavailable); this is NOT a
    crashed land -- whoever owns the root checkout directly (most often the
    coordinator) must commit or stash it, an agent cannot fix this by retrying
    ERROR: ticket land failed: DirtyMain: root checkout has uncommitted changes

`git --no-optional-locks status --short` in the root immediately afterwards
returned ZERO lines. The root was clean. A retry of the identical land command
succeeded with no intervening change to the tree.

THE TELL IS IN THE MESSAGE ITSELF: "(git status unavailable)". That is where the
list of dirty paths should be. The guard's own `git status` call FAILED -- almost
certainly index.lock contention, since a concurrent land for T-2942 was running
at that moment -- and the guard converted that failure into an assertion that the
tree is dirty.

WHY THIS IS THE PROJECT'S DOMINANT BUG CLASS, INVERTED. Everywhere else the
hazard is an unmeasured result rendering as CLEAN. Here an unmeasured result
renders as a POSITIVE FINDING. Both are the same defect: a failed measurement
being reported as a measurement. This one is more expensive than it looks
because the message is actively misleading -- it names the coordinator, states as
fact that untracked work exists, and instructs a human to commit or stash
something that is not there. It also says "an agent cannot fix this by retrying",
which is exactly wrong for the transient case: retrying is precisely what fixed
it.

DO NOT FIX THIS BY FAILING OPEN. A guard that skips the dirty check when it
cannot read status would let a genuinely dirty root through, and DirtyMain exists
because a dirty root corrupts concurrent lands. Failing closed is correct. The
defect is that an UNREADABLE status is reported as a KNOWN-DIRTY status.

WHAT TO BUILD:
  1. Distinguish the three states in both the code and the message: CLEAN,
     DIRTY (with the offending paths listed), and STATUS-UNREADABLE (with the
     underlying git error). Refuse on the third as now, but SAY it is unreadable
     rather than asserting dirt.
  2. When the cause is contention, say so and say retrying is appropriate. The
     current text tells the reader the opposite.
  3. Consider a bounded retry of the status call itself before refusing --
     index.lock contention under a live fleet is expected, not exceptional, and
     this repo runs many concurrent lands by design. If a retry is added, bound
     it and log each attempt; do not loop unbounded.

MUST-FIRE FIXTURE: a genuinely dirty root still refuses, and the message lists
the offending paths.
MUST-STAY-QUIET FIXTURE: a clean root passes.
THIRD FIXTURE (the actual bug): a root whose `git status` invocation fails
produces a STATUS-UNREADABLE refusal naming the git error -- never a message
claiming uncommitted work exists.

CHECK FOR SIBLINGS. This is unlikely to be the only guard that treats a failed
subprocess as a positive finding. Grep the land path and the gate family for
other places where a non-zero git/subprocess exit is folded into a "found
something" branch, and report the count. Do not fix them all here -- report them
so they can be filed individually.

ACCEPTANCE
- The three states are distinguished in code and in the operator-facing message.
- All three fixtures present.
- The misleading "an agent cannot fix this by retrying" text is corrected for the
  unreadable/contention case.
- A stated count of sibling guards that fold a failed subprocess into a positive
  finding, filed separately rather than fixed here.
