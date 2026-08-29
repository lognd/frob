---
id: T-3407
title: 'fleet_status reports forkservers healthy while they hold 12.5GB RSS: it measures
  orphan status and swap, never resident memory'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
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
fleet_status.py's forkserver reporting measures ORPHAN STATUS and SWAP, never
RESIDENT MEMORY, so a coordinator reading it concludes forkservers are healthy
at the exact moment they are consuming almost all of the host's RAM.

MEASURED 2026-08-29, one invocation, both halves within seconds of each other.

fleet_status said:

    LOAD 39.7  MEM 1.2GB avail  (SWAP 2.6GB in use -- real memory pressure)
    ORPHANED FORKSERVERS: 0
    STALE FORKSERVERS: 0
    SWAP HELD BY FORKSERVERS: 0.0GB
    CONCURRENT CHECKS: 7 (T-2473, advisory)

Direct measurement said:

    ps -eo rss,args | aggregate by command
      forkserver   12.5 GB RSS
      frob-check    8.2 GB RSS
      other         1.9 GB
      pytest        0.1 GB

Every one of those forkservers is live-parented, so all three forkserver lines
are literally correct and all three are reassuring. The host had 1.2GB
available. Forkservers held 12.5GB.

THE DEFECT IS THE CHOICE OF METRIC, not an arithmetic error. The three
forkserver lines answer "are there leaked forkservers?" -- a question that grew
out of T-2517's real orphan-leak incident, where 94 orphans held 17GB of swap.
That fix taught the script to watch orphans and swap. It never taught it to
watch resident memory of HEALTHY forkservers, which is the failure mode when the
fleet is simply running too many concurrent checks. Both end in the same place:
an OOM killer that destroys agent sessions mid-ticket.

WHY THIS IS COORDINATOR-CRITICAL. fleet_status exists to answer "is it safe to
dispatch?". Its dispatch guidance line already reads memory ("guidance is 1
agent"), so the information is present -- but the forkserver section actively
contradicts it, and the forkserver section is the one that names a CAUSE. A
coordinator who sees "MEM 1.2GB" and "ORPHANED 0 / STALE 0 / SWAP 0.0GB"
reasonably concludes the memory is going somewhere other than forkservers and
looks elsewhere, or worse, treats the guidance as conservative. This repo has a
documented prior incident of OOM kills destroying agent sessions.

CONCURRENT CHECKS is marked "(advisory)" and is the actual lever: 7 concurrent
`frob check` runs times roughly 1.8GB of forkservers each is the whole 12.5GB.
Advisory-only means nothing enforces it.

WHAT TO BUILD
1. Report forkserver RSS alongside orphan/stale/swap, and make the total the
   headline rather than a sub-line. State the count and the aggregate RSS.
2. Attribute RSS to concurrent checks so the causal chain is visible: N checks
   -> M forkservers -> X GB. The coordinator needs the lever, not just the
   symptom.
3. Decide whether CONCURRENT CHECKS should stay advisory. If a hard cap is
   wrong -- and there is a real argument that it is, since a coordinator
   sometimes must run a check during a busy fleet -- then say so explicitly and
   make the advisory line carry the RSS consequence instead. Do not add a cap
   silently; T-2473 chose advisory deliberately and that choice deserves an
   argument, not a quiet reversal.

DO NOT simply add a fourth forkserver line and call it done. The problem is that
three reassuring lines outrank one alarming one. Consider whether the section
should lead with the aggregate.

MUST-FIRE FIXTURE:   healthy, live-parented, non-swapping forkservers holding
                     large RSS produce a visible warning.
MUST-STAY-QUIET:     a small number of forkservers on an idle host does not.

ACCEPTANCE
- RSS reported and attributed to concurrent checks.
- The advisory-vs-cap question answered in prose, either way, with reasoning.
- Both fixtures committed.
