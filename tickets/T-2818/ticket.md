---
id: T-2818
title: 'fleet_status reports 0 orphaned forkservers while 90 leaked ones hold 13GB:
  the orphan check tests only the immediate parent, not the ancestry root'
state: queued
kind: bug
origin: agent
created: '2026-08-21'
priority: high
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured 2026-08-21

The box reached 1.6GB available RAM and 16.7GB swap, with zero lands
completing for 45 minutes. Meanwhile `scripts/fleet_status.py` reported:

    ORPHANED FORKSERVERS: 0
    STALE FORKSERVERS: 0
    SWAP HELD BY FORKSERVERS: 13.9GB

Zero orphaned, zero stale -- and 13.9GB held. Those two lines cannot both
be describing a healthy system, and the operator (me) read the 0/0 as
"nothing to reap" for over an hour while the machine degraded.

Ground truth at that moment:

    92 processes matching `multiprocessing.forkserver`
     1 live `frob check` process (306s old)
     0 live `frob check` processes minutes later

Forkserver ages: 16990s, 6060s, 3969s, 3062s. A full unbudgeted `frob
check` on this repo takes ~334s. Nothing older than a few hundred seconds
can belong to a running check.

Reaping every forkserver older than 1800s (90 processes, chosen because no
legitimate check lives that long) while zero checks were running:

    swap        16.7GB -> 3.2GB
    available    1.6GB -> 18.7GB

## Root cause: the orphan check only looks ONE level up

The leaked forkservers are parented to OTHER FORKSERVERS, not to a live
`frob check`. Sampled parents:

    ppid=1550827  age 16970s  -> itself a forkserver
    ppid=3031727  age  6060s  -> itself a forkserver
    ppid=3247242  age  3969s  -> itself a forkserver

So every one of them HAS a live parent, and a one-level parent-liveness
test classifies it as "live-parented" -- healthy. The parent is itself
leaked. The classification never walks the chain to ask whether the ROOT
of the tree is a live `frob check`.

Net effect: a forkserver tree whose originating check died hours ago
reports as entirely healthy, indefinitely, while holding gigabytes.

## Why this matters beyond the memory

The operator makes dispatch and concurrency decisions from these numbers.
Reading `ORPHANED: 0 / STALE: 0` I held the fleet at reduced agent count
and hunted the wrong cause (I attributed the pressure to genuine
concurrent-check working set, and said so). The detector did not merely
fail to help -- it actively pointed away from the real problem. That is
the silent-zero class this repo treats as its dominant bug (epic T-2391):
"could not classify" rendering as "nothing found".

Note also this is a RECURRENCE. T-2443 recorded the same shape: ~94
orphaned forkservers holding 17GB, presenting as agent stalls, with RSS
reading ~0 for swapped processes so `VmSwap` had to be summed instead.
The swap-summing half was fixed (T-2517 is cited in the very line that
reported 13.9GB). The ORPHAN CLASSIFICATION half was not.

## Required shape

Classify a forkserver by whether its ancestry chain reaches a LIVE
originating `frob check` process, not by whether its immediate parent
happens to be alive. Walk to the root of the tree.

An age-based backstop is also worth having and is cheap: a forkserver
older than some multiple of the longest legitimate check duration cannot
belong to a live check regardless of ancestry. Derive that duration from
recorded timings rather than hardcoding it -- `.frob/check-budget-timing-samples.json`
now exists (T-2809) and holds real per-group stage samples. Do NOT
hardcode a threshold; this repo has already been bitten twice by a
constant that never tracked repo growth (T-2715, and its desynced twin
`_TRUE_COUNT_BUDGET_S`).

Consider also whether `fleet_status` should refuse to report `0 orphaned`
while simultaneously reporting multi-gigabyte forkserver swap. Those two
readings are mutually implausible and the combination should be surfaced
loudly rather than left for a human to notice.

## Positive controls, both directions

- A forkserver whose parent is another forkserver whose originating check
  is DEAD must be reported ORPHANED. Plant a two-level chain and kill the
  root; this is the case that fails today.
- A forkserver belonging to a genuinely RUNNING check must NOT be reported
  orphaned, at any chain depth. Without this the fix reaps live work
  mid-check, which is far worse than the leak.
- Zero forkservers at all must report 0 without error.

## Reaping

Whatever reaps these must verify no live check is running at the moment of
the kill, and re-verify immediately before sending signals -- I aborted my
own reap on that condition. A reap that races a starting check kills its
workers mid-run.
