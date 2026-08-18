---
id: T-2443
title: 'frob check leaks multiprocessing forkservers: 94 orphans held 17GB of swap
  and stalled the fleet'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a frob check killed mid-run by SIGTERM or a budget abort, when it exits,
    then no multiprocessing forkserver from that run remains alive reparented to init.
  evidence: []
- text: Given a normally completing frob check, when it runs, then its gates still
    execute in parallel and produce identical findings, proving the leak was not fixed
    by serialising the pool.
  evidence: []
- text: Given orphaned forkservers present on the machine, when fleet_status.py runs,
    then it reports their count alongside the existing swap-pressure guidance.
  evidence: []
threat: null
component: process
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18, on a live fleet. `frob check` (and/or the pytest
runs it drives) leaks `multiprocessing.forkserver` processes that
outlive their parents indefinitely.

    total forkserver processes:      116
    older than 1 hour:                94   (oldest 15368s = 4.3 hours)
    swap held by forkservers:      17314 MB
    ancestry check on all 94:      100% reparented to /init (pid 620),
                                   i.e. their creating process is DEAD;
                                   0 of 94 had any live ancestor

System state before reclaim: 18GB of 24GB swap consumed, MemAvailable
10GB, load average 13.70 and climbing.

After terminating exactly those 94 (SIGTERM, all exited cleanly, no
SIGKILL needed; the 22 young forkservers belonging to two genuinely
in-flight lands were left alone and both lands survived):

    swap:            18GB -> 10GB
    MemAvailable:    10GB -> 17GB
    used:            12GB ->  5GB
    forkservers:      116 ->  9

OBSERVED CONSEQUENCE, not theoretical. Two agents stalled with "no
progress for 600s" while this was accumulating, and `scripts/
fleet_status.py` had dropped its own dispatch guidance to "1 agent
(SWAP 18.4GB in use -- real memory pressure MemAvailable does not
show)". The leak silently converts a healthy 5-agent fleet into a
stalling 1-agent fleet over a few hours, and the symptom (agents
hanging) looks nothing like the cause (process leak), so it gets
misattributed to the agent, the model, or the harness. I misattributed
the first stall myself.

It also starves the thing meant to fix verification debt: the deferred
drain runs `frob check --budget 300`, so a swapping machine makes the
drain slower exactly when the backlog is largest.

WHERE TO LOOK. `frob check` runs gates in parallel via a process pool
(`frob.process`, and the `_check_chunking` stage machinery). A
`multiprocessing` forkserver should die with its parent; 94 reparented
to init means the pool is not being shut down cleanly on at least one
exit path -- likely the budget-exhausted / timed-out / killed path
rather than the normal one, which would explain why this accumulates
under load and during the 540s-wrapper kills this fleet routinely
takes. Check that pools are closed in a `finally` (or context manager)
covering SIGTERM and budget-abort, not only the success return.

FIX SHAPE:
  - Ensure the pool/forkserver is torn down on EVERY exit path,
    including budget abort, timeout, and signal death.
  - Consider a startup reaper: on `frob check` start, terminate
    forkservers belonging to this repo's venv that are reparented to
    init and older than a threshold. Defensive, but this leak is
    invisible to the operator until the machine swaps.
  - Surface it: `scripts/fleet_status.py` already reports swap
    pressure; have it also report orphaned-forkserver count, since that
    turns an unexplained "guidance is 1 agent" into an actionable
    number.

POSITIVE CONTROLS:
  - must-now-clean: run `frob check` and kill it mid-run (SIGTERM, and
    separately a budget abort); assert zero forkservers remain
    reparented to init afterwards.
  - must-still-work: a normal completing `frob check` still runs its
    gates in parallel and produces identical findings -- do not fix
    this by serialising the pool away.
