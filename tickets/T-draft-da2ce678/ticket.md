---
id: T-draft-da2ce678
title: 'verify: single-instance full checks with memory admission; name the stage
  when the pass is unmeasurable; stop 30-min blocks on a stale watermark'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: critical
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/verify/
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/coord/_status.py
- tests/unit/verify/
- docs/modules/tickets-verify-sweep.md
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
Measured 2026-09-25 12:30 UTC on the coordinator host (23 GB RAM): four
concurrent `frob check --json` processes at 1.8-2.4 GB RSS each, plus
the land drain at 2.2 GB, drove free memory to ~1 GB and the session
harness started reaping idle background loops. The four checks were:

  - the land's own post-land `frob ticket sweep-async <id>` child
  - a `frob verify drain-async` child (backpressure debouncer)
  - a coordinator diagnostic full check
  - one older full check of unknown parent

and the verify worker's pass itself never produces a parsable result on
this repo any more (watermark stuck 36 h at 9e0c89bb; `frob verify now`
at load 4 still ends "no parsable result -- gates stage never ran"), so
each of those verify checks is 2 GB of RAM and ~25 min of CPU spent to
learn nothing, while every land then blocks up to 30 min on the
backpressure ceiling it cannot clear.

Deliver (tiered safety):
1. Single-instance verify: `verify drain-async`/the debouncer must not
   spawn a full check while another verify pass or a land's own sweep is
   running on the same root (guaranteed safe: it is redundant work);
   log the skip with the pid it deferred to.
2. Memory admission for full checks: the check runner's existing
   `_compute_admitted_workers`/per-worker budget must refuse (or defer)
   a new full check when available memory is below the per-check RSS
   the last N runs measured, naming the number; the verify worker treats
   that refusal as "not now", not Unmeasurable.
3. Diagnose why the full check reaches no gate-summary at root: capture
   the child's last stage/stderr tail into the verify-drain log (today
   the log has only the generic warning), and reproduce with the
   thousand-commit `git diff <watermark> --unified=0` that exceeds the
   30 s spawn budget (T-5818 raises the budget; verify must also chunk or
   skip that diff when the watermark is that far behind).
4. Backpressure sanity: when the watermark is older than max_age by more
   than 24 h, the land's 30-min block is pure loss; report it as a
   quarantined condition once (coord status) instead of blocking every
   land, until a verify pass succeeds.
5. Positive control: fixture with a stale watermark + a running sweep
   shows the debouncer skips; a low-memory simulation shows the refusal
   path; the reproduction in (3) yields a named stage in the log.
