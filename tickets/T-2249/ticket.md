---
id: T-2249
title: fleet_status's concurrency guidance keys on MEM available, which read 11.5GB
  healthy while the machine was already swapping 6GB with 0 free RAM
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'With swap in use, the report surfaces it and the concurrency guidance reflects
    the pressure (fails today: swap never read, guidance is a static string)'
  evidence: []
- text: 'MUST-STILL-PASS: on a machine with SwapTotal 0, no false pressure claim and
    no crash (division by zero total)'
  evidence: []
- text: Existing LOAD/MEM figures reported unchanged -- this adds a signal, does not
    replace them
  evidence: []
- text: Reads /proc/meminfo directly, consistent with existing MemAvailable handling;
    no subprocess, no new dependency
  evidence: []
- text: State the measured basis for any threshold chosen
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# fleet_status's concurrency guidance keys on "MEM available", which reads healthy while the machine is already swapping GBs

## Measured evidence (2026-08-16)

fleet_status reported, and I dispatched against it:

    LOAD 30.9  MEM 11.5GB avail  7 live lease(s) -- guidance is 3-4 agent concurrent

11.5GB available looks comfortable. The actual machine state at that moment:

    Mem:    23 total, 13 used,  0 free, 10 buff/cache, 10 available
    Swap:   24 total,  6 used, 17 free          <-- 6GB already swapped out

`available` counts reclaimable page cache and says NOTHING about pages the
kernel has already pushed to swap. So the one memory number the report shows
was healthy precisely while the system was under real pressure. Free RAM was
literally 0.

`git grep -nE "swap|Swap|SwapFree" -- scripts/fleet_status.py` returns nothing:
swap is not read at all.

## Why this matters more than a cosmetic gap

The `guidance is 3-4 agent concurrent` clause is attached to this line, which
makes it the coordinator's concurrency governor -- the same structural mistake
T-2222 fixed for the LEASE count (a raw number with advice welded to it). I
ran 7 concurrent agents across several cycles partly because the memory figure
never looked alarming. This repo has already lost a session to the OOM killer
under exactly this condition; the recorded remedy ("cap agents at 3-4") is a
rule the operator must remember, precisely because the instrument does not
show the pressure.

Load average did not substitute for it: load climbed 15.9 -> 25.7 -> 26.9 ->
30.9 across four checks, but load is ambiguous here (it counts I/O wait and
this box runs many short-lived subprocesses), so it never read as a hard stop.
Swap-in-use is the unambiguous signal and it was invisible.

## Do NOT fix it this way

- **Do NOT just print a raw swap number next to the others.** The defect is
  that the GUIDANCE keys on the wrong quantity. If swap-in-use is the real
  pressure signal, the concurrency advice must reflect it, or the operator
  reads three numbers and still trusts the reassuring one.
- **Do NOT use load average as the pressure signal.** Measured above: it rose
  monotonically while nothing was wrong yet, and it counts I/O wait. It cannot
  distinguish "busy" from "over-committed".
- **Do NOT hardcode a swap threshold without measuring.** State the basis for
  whatever number you pick. A machine with a large swap file legitimately uses
  some; "any swap at all" is not automatically pressure.
- **Do NOT shell out to `free`.** fleet_status is deliberately import-light and
  reads `/proc` directly elsewhere (`MemAvailable`); `/proc/meminfo` carries
  `SwapTotal`/`SwapFree` in the same read. Stay consistent with the file's own
  contract.

## Acceptance criteria

1. (MUST FAIL FIRST) With swap in use, the report surfaces it and the
   concurrency guidance reflects the pressure. Fails today: swap is never read,
   and the guidance is a static "3-4" string regardless of machine state.
2. MUST-STILL-PASS CONTROL: on a machine with NO swap configured
   (`SwapTotal: 0`), the report must not claim pressure and must not crash --
   division by a zero total is the obvious way to break this.
3. The existing LOAD / MEM figures continue to be reported unchanged; this
   ADDS a signal rather than replacing the ones already relied on.
4. Reads `/proc/meminfo` directly, consistent with the existing MemAvailable
   handling. No subprocess, no new dependency.
5. State the measured basis for any threshold chosen.

## Scope note

`scripts/fleet_status.py`. NOTE: T-2213 and T-2229 are also queued against this
same file. Dispatch all three as ONE series to ONE agent -- they cannot run in
parallel (scope is the lease), and the coordinator has already caused one
self-collision by dispatching same-file tickets separately.
