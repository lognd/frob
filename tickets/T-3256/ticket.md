---
id: T-3256
title: 'Six concurrent frob check runs drive the box to zero free memory: each sizes
  its pool against the whole machine, with no cross-process budget'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'coordinator-supplied live evidence: a land killed by its own 540s wrapper
    while its child frob check was actively progressing (335s, 82.8% CPU), plus lock-starvation
    of non-landing ledger ops during the same window; verified independently before
    folding into fix design'
  actor: logan
  at: '2026-08-28'
  old_length: 3750
  new_length: 6150
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-28 with six agent series live on a 12-core / 23 GB box:

    load average          35.89 (1min), 30.37 (5min), 25.83 (15min)
    memory                18 GB used, 0 GB free, 4 GB available
    swap                  engaged
    frob check processes  6 concurrent, from six different worktrees
    forkserver processes  51
    forkserver RSS total  14,552 MB

Every one of those forkservers was YOUNG (137-194 seconds). This is NOT the
known orphaned-forkserver leak -- these are live, legitimate `frob check` runs.
That is what makes it a design problem rather than a cleanup problem: the system
behaved exactly as designed and drove the box to zero free memory.

THE DEFECT. Each `frob check` sizes its own process pool against the machine's
total CPU count. Six of them run concurrently and each believes it has the whole
box. There is no cross-process budget, no admission control, and nothing that
knows how many checks are already running. 6 x (a pool sized for 12 cores) on a
12-core box is a 6x oversubscription that no single component is wrong about.

WHY THIS COSTS REAL WORK, NOT JUST SPEED. This repo already has recorded
history here:
  - Session kills traced to the WSL OOM killer, which produced a standing
    operational rule to cap the fleet at 3-4 agents.
  - Concurrent lands thrashing: each land spawns its own `frob check`, so N
    simultaneous lands slow each other roughly N-fold.
  - A land killed mid-flight can write `state: done` with zero code on main.
That last one is the reason this is filed as a bug and not a performance nit:
memory pressure that kills a land does not merely slow things down, it can
corrupt the ledger. An OOM kill is indistinguishable from a timeout at the point
where it lands.

THE OPERATIONAL RULE IS A WORKAROUND, NOT A FIX. "Cap the fleet at 3-4 agents"
is knowledge that lives in an operator's head. Per the standing directive that
repeated friction should be fixed globally in the tooling rather than
remembered, this belongs in frob. An automatic mechanism beats a documented
limit, because a documented limit requires knowing the document exists.

WHAT TO BUILD -- measure before choosing:
  1. A cross-process admission budget for `frob check` pool sizing. The
     candidates are a shared lock/semaphore keyed on the repo, a token file
     under .frob/, or each check sizing its pool against OBSERVED current load
     rather than nproc. Say which you chose and why, with a measurement.
  2. It must DEGRADE, not refuse. A check that cannot get its full pool should
     run with a smaller one and SAY SO. Refusing to run turns a resource
     constraint into a false green, and this repo's dominant defect class is a
     failed measurement reported as a successful one.
  3. Memory, not just CPU, is the binding constraint here: 14.5 GB of
     forkservers on a 23 GB box. A budget that counts only cores will not
     prevent what was measured above. Size against both.

DO NOT FIX THIS BY LOWERING THE POOL SIZE UNCONDITIONALLY. A single `frob check`
on an idle box should keep using the whole machine -- that is the common case
and it is already slow enough that gates get skipped under budget pressure.
The fix must be adaptive to what else is running.

MUST-FIRE FIXTURE: N concurrent checks do not collectively oversubscribe the
box; the later ones run with reduced pools and announce it.
MUST-STAY-QUIET FIXTURE: a single check on an idle box gets its full pool, with
no announcement and no slowdown.

ALSO REPORT, DO NOT FIX HERE: whether `fleet_status` can see this condition at
all. An operator watching the fleet should be able to tell "six checks are
fighting over the box" from "six agents are stalled", and those look identical
from the outside today.


FIRST MEASURED CASE OF THIS CONTENTION KILLING A LAND, not merely slowing one.
2026-08-28, observed live from the coordinator.

Series DP's `frob ticket land T-3246` ran to its `timeout 540` wrapper and was
killed. At the moment of death:

    land pid 3521399        age 540s (wrapper budget exhausted)
    child frob check        age 335s, 82.8% CPU
                            (`frob check --ticket T-3246`)

The child was doing real work at full CPU. This was not a deadlock, not a stall,
and not a defect in the ticket's own changes. The land simply could not finish
inside 540 seconds because five other series were landing concurrently and every
land spawns its own full `frob check`.

AFTERMATH, verified: T-3246 remained `state: in-progress` with no land commit on
main. Nothing was half-written this time. That matters, because this repo has a
recorded failure mode where a timed-out land writes `state: done` with evidence
while ZERO code reaches main -- so the cost of this contention is not bounded by
"the agent retries". A land killed at the wrong instant can corrupt the ledger.

WHY THIS SHARPENS THE TICKET. The original filing argued from resource
measurements (load 36, 0 GB free, 51 forkservers, 14.5 GB RSS) and from prior
recorded history. This is a direct causal observation: oversubscription consumed
a land's entire wall-clock budget while it was actively progressing. The 540s
wrapper is not generous or stingy in itself -- it is simply not a fixed quantity
when N unbudgeted checks share 12 cores.

CONSEQUENCE FOR THE FIX, and this is the part that should change the design: any
solution that only makes checks share CPU more politely still leaves each land
racing a FIXED wall-clock timeout. Consider whether the land's timeout should be
budget-aware (extended when the check is demonstrably progressing) as well as
whether the pool should be smaller. State which you chose. Do NOT simply raise
the 540s wrapper -- an unbounded land is worse than a killed one, and the
timeout is what makes a genuinely wedged land fail fast.

ALSO WORTH COUNTING: the coordinator was refused the ledger lock on three
consecutive `frob ticket close` attempts during the same window, and frob's own
[REPEATED_FAILURE] guard correctly told it to stop. Lock starvation of
non-landing operations is a second, distinct symptom of the same
oversubscription and belongs in the same analysis.
