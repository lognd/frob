---
id: T-2807
title: wait_for_land_slot reports a free slot during the window where frob's own T-1619
  process scan still refuses LandInProgress
state: in-progress
kind: bug
origin: agent
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/wait_for_land_slot.py
- tests/unit/test_wait_for_land_slot_unattributed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_wait_for_land_slot_unattributed.py
  reason: new evidence test file (test_coordinator_scripts.py is leased by T-2755)
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured 2026-08-21

`scripts/wait_for_land_slot.py` (T-2775) reported a free slot, and the very
next `frob ticket new` refused:

    slot free: LANDS IN FLIGHT=0 <= max-in-flight=0 after 10.9s
    ...
    WARNING: refused -- a `frob ticket land` process (pid 2063641) is running
      against this repository for an unknown ticket, even though its
      land.lock is not currently held (T-1619 belt-and-braces process scan)
    ERROR: ticket new: refused -- LandInProgress

Hit twice by me within ten minutes, and twice by the agent working T-2796
("Two `ticket work`/`land` attempts hit LandInProgress/lock-timeout and were
retried"). It is reproducible, not a one-off race.

## Root cause: two different definitions of "a land is in flight"

- `wait_for_land_slot.py` reuses `scripts/fleet_status.py`'s
  `LANDS IN FLIGHT: N` line. That was a deliberate and correct design choice
  (do not write a second definition), and it is the SAME source the
  coordinator reads.
- `frob ticket new` / `land` refuse via T-1619's belt-and-braces PROCESS
  SCAN, which additionally catches a `frob ticket land` process that is
  running but whose `land.lock` is not held YET -- the startup window
  between spawn and lock acquisition.

So the wait primitive can legitimately say "free" during a window in which
frob will still refuse. Both are individually correct; they just answer
different questions.

## Why it matters

The whole point of T-2775 was to give agents ONE reliable precondition so
they stop hand-rolling poll loops. A primitive that says "clear" and is then
immediately refused trains agents to distrust it and go back to hand-rolled
loops -- which is exactly the failure mode it was built to end. It also
wastes a land attempt, and under the current ~300s-per-check cost that is
not cheap.

## Required shape

Make the wait primitive answer the SAME question frob's refusal asks. The
preferred direction is to reuse T-1619's own process-scan predicate rather
than adding a third definition -- there are already two, and a third is how
this class of bug recurs. If that predicate is not importable from a script,
say so and propose where it should live rather than duplicating its logic.

Do NOT solve this by having the script sleep an arbitrary extra few seconds.
That converts a correctness gap into a timing gamble, and it will fail under
load exactly when it matters most.

Consider also whether `fleet_status.py`'s own `LANDS IN FLIGHT` should adopt
the broader definition. The coordinator makes dispatch decisions from that
number, so if it under-reports during the startup window, every consumer is
affected, not just this script.

## Positive controls, both directions

- A land process running with its lock NOT yet held: the script must NOT
  report a free slot. Plant this by starting a land and sampling during the
  startup window.
- No land process at all: the script must still return 0 promptly. Without
  this the fix degenerates into "never reports free".
- The existing three exit codes (0 free / 1 timeout / 2 could-not-measure)
  must keep their meanings, and a failed probe must still be UNMEASURED
  rather than free.

## Note

This is a follow-up to T-2775, not a defect in its design -- reusing
fleet_status was the right call at the time and prevented a worse
duplication. The gap is that frob's own refusal uses a broader predicate
than the one fleet_status reports.
