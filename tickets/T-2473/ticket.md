---
id: T-2473
title: frob check has no global concurrency limit, so a busy fleet swaps and throughput
  drops as agents are added
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given more simultaneous frob check requests than the machine can support,
    when they run, then the number actually executing concurrently is bounded, or
    is accurately reported for a caller to act on.
  evidence: []
- text: Given a single frob check on an idle machine, when it runs, then it completes
    with no added latency and no new failure mode.
  evidence: []
- text: Given a check that is queued or refused under the limit, when it is deferred,
    then the deferral is visible rather than the work being silently skipped.
  evidence: []
- text: Given fleet_status.py, when it reports machine conditions, then it includes
    the count of concurrently running frob check processes alongside its existing
    swap and orphaned-forkserver lines.
  evidence: []
threat: null
component: process
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket land` serializes on `land.lock` -- only one land runs
repo-wide. `frob check` has NO equivalent global limit, so N agents can
run an unbounded number of simultaneous full checks, each of which is
one of the heaviest processes this repo produces.

MEASURED just now, with six implementer agents active:

    concurrent `frob check` processes:    12
    live forkserver processes:            93   (0 orphaned -- all belong
                                               to those live checks)
    per-check RSS:                        0.5 - 1.1 GB
    swap in use:                          7.8 GB  (was 2.1 GB at 4 agents)
    load average:                         21.0    (was 15.7)
    lands completed per hour:             6       (was 9)

So throughput went DOWN as agent count went up. The machine has 23GB
total; twelve concurrent checks at ~0.7GB average is most of it before
anything else runs, and the overflow goes to swap, which slows every
check, which lengthens the window in which they overlap.

This is now the binding throughput constraint. The other serialization
points found today have been fixed or are in flight -- CHANGELOG
fragments (T-2445), the version bump (T-2462), the gate-rule registry
(T-2454), foreign-draft finalization (T-2425) -- and with those removed,
what remains is simply that the fleet can saturate the machine with
checks nobody is coordinating.

Note `frob check` is separately measured at roughly 71% of agent wall
time, so this is not a marginal cost.

RELATED BUT DISTINCT, do not conflate: T-2443 fixed a LEAK (94 orphaned
forkservers holding 17GB of swap, surviving their dead parents). That is
fixed and confirmed not recurring -- the 93 forkservers measured here
are all live children of running checks, which is correct behaviour.
This ticket is about legitimate concurrent demand exceeding capacity,
not about leaked processes.

FIX SHAPE -- judgement wanted, several options with real tradeoffs:
  - A global advisory concurrency limit on `frob check` (a lock or
    semaphore permitting K simultaneous runs, K derived from CPU/RAM
    rather than hardcoded), with waiters queueing rather than failing.
    Simple, but risks turning a busy fleet into a queue of stalled
    agents unless K is chosen well and waiting is bounded.
  - Make the limit ADVISORY and observable instead of enforced: have
    `frob check` report how many other instances are running and how
    much memory is available, so an agent (or `fleet_status.py`) can
    make an informed decision. Cheaper, and matches this repo's
    preference for surfacing over commanding.
  - Reduce per-check cost rather than concurrency -- but note the land
    budget was just RAISED (300 -> 480, T-2456) because the previous
    budget was silently dropping a whole stage group from every sweep,
    so trimming work is not freely available.

`scripts/fleet_status.py` already reports swap pressure and orphaned
forkserver count, and already emits a dispatch guidance number. It
should also report CONCURRENT CHECK COUNT -- that is the number a
coordinator actually needs to decide whether to dispatch, and it is
currently invisible.

POSITIVE CONTROLS:
  - must-now-bound: with the fix in place, K+1 simultaneous check
    requests result in at most K running concurrently (or, for the
    advisory variant, the count is accurately reported).
  - must-not-stall: a single check on an idle machine runs with no
    added latency and no added failure mode.
  - must-still-complete: work does not silently drop because a check
    was refused or queued -- a deferred check must be visibly deferred,
    per the fail-loudly doctrine (T-2391), not skipped.
