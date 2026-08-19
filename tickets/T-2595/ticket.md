---
id: T-2595
title: Lock or CAS-write .frob/rapid-sweep-baseline.json against concurrent detached-sweep
  writers
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
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
T-2571 fixed two defect classes behind the deferred post-land sweep's
false-positive regression filings: phantom findings against a
land-deleted file (fixed), and detecting -- but not preventing -- a
concurrent-sweep clobber of .frob/rapid-sweep-baseline.json.

The rolling baseline file lives at the shared checkout root (T-1684 by
design: every land's own detached, off-critical-path sweep operates
against the SAME root), and concurrent lands routinely spawn concurrent
sweeps in this fleet. Two sweeps can race: sweep B reads the baseline
before sweep A's write lands, computes its own new_findings diff against
a baseline that is already stale, and B's own subsequent write can in
turn discard whatever A just recorded. T-2571's own
_baseline_write_survived makes this race DETECTABLE (logs a WARNING
naming the sweep/commit when a write does not survive) but does not
prevent it -- the plausible mechanism behind an identical (rule, file)
identity set recurring as "new" across 3+ consecutive, otherwise
unrelated sweeps (measured across T-2381/T-2474/T-2525/T-2560).

Fix the race itself: either a file lock (flock, matching land.lock's own
posture) around the read-modify-write of
.frob/rapid-sweep-baseline.json, or a compare-and-swap write (read the
current commit, write only if it still matches what this sweep read
before computing fresh, else re-read-merge-retry). Either approach must
not turn concurrent sweeps into a serialization bottleneck (rapid's
whole point is staying off the land critical path, T-1684) -- a lock
held only for the tiny read+write itself, not the multi-minute frob
check in between, is the shape to aim for.
