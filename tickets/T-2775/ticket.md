---
id: T-2775
title: no shared primitive for 'wait until a land slot is free', so every agent hand-rolls
  a noisy poll loop that misreads failure as zero
state: in-progress
kind: feature
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
- scripts/
- docs/guides/coordinator-scripts.md
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: T-2775's own brief requires positive-control unit tests for the new script
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

Every agent in a landing fleet needs the same thing before landing: block
until no other land is in flight. There is no shared primitive for it, so
each agent hand-rolls a poll loop, and they are hand-rolled WRONG in ways
that have cost real time today:

- Loops that `echo` once per tick emit a line every 30s into the agent's
  context. A 9-minute wait is ~18 lines of pure noise, repeated per agent
  per land. Across a 5-agent fleet this is a continuous context tax that
  buys nothing.
- Loops that read the count without checking the exit code treat an empty
  string from a FAILED `fleet_status.py` as a genuine zero, and then start
  a second concurrent land -- the exact condition being waited out. This
  is the repo's dominant bug class (silent zero, epic T-2391) reproduced
  in the workaround for it.
- Agents that "wait for a notification" instead of polling park forever
  with committed work stranded in a worktree. Observed at least four times
  today.
- Callers disagree on the threshold and on their own wrapper timeout
  (`timeout 500` vs `timeout 540` seen in the same fleet minute).

## Required shape

One script under `scripts/`, alongside the existing `fleet_status.py` and
`check_summary.py`, documented in `docs/guides/coordinator-scripts.md`
(that guide already exists and is the established home).

Behavior:
- Blocks until no land is in flight, then exits 0.
- QUIET by default: no per-tick output. Print ONE summary line on exit
  stating what was waited on and for how long. A `--verbose` flag may
  restore per-tick lines for debugging.
- Bounded by an explicit `--timeout`, defaulting BELOW the caller's usual
  wrapper so it declines cleanly rather than being killed. Exits NONZERO
  with a distinct, documented code on timeout so a caller can tell
  "slot free" from "gave up" from "measurement failed".
- Treats an unreadable/failed status probe as UNMEASURED -- never as zero.
  Retries; if it cannot measure for the whole timeout it exits with the
  measurement-failure code, and says so.
- Reuses `fleet_status.py`'s existing logic rather than re-deriving how a
  land is detected. Do NOT add a second definition of "a land is in
  flight"; two homes for that rule will desync.

## Positive controls, both directions

- With a land genuinely in flight, the script BLOCKS and does not return 0
  early.
- With no land in flight it returns 0 promptly (it must not impose a
  fixed sleep on the common uncontended case).
- With the status probe forced to fail, it exits with the
  measurement-failure code and NOT 0 -- proving an unmeasurable state can
  never be mistaken for a free slot. Without this case the script
  reintroduces the silent zero it exists to prevent.
- On timeout it exits with the timeout code, distinct from both above.

## Related

Pairs with T-2774, which fixes the same contention structurally inside
`frob ticket land` itself. This ticket is the caller-side primitive; T-2774
is the tool-side refusal. Neither replaces the other -- a caller can always
be killed, and the tool should still decline rather than die.
