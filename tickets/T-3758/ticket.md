---
id: T-3758
title: 'deprecated-baseline lock producer is unwired: tighten_deprecated_baseline
  has no production caller, so DEPR005 baseline can never re-stamp'
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: tracking/decision ticket, not implemented in this pass;
  interim pin filed as separate ticket
body_changes:
- mode: set
  reason: record investigation of unwired DEPR baseline producer
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 1328
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
tighten_deprecated_baseline (src/frob/gates/_deprecated_baseline.py) is the
ONLY writer of frob-deprecated-baseline.lock.json, but it has no production
call site anywhere in src/ -- it is called only from
tests/unit/gates/test_deprecated_baseline.py. It was never wired into
`frob ticket land`, so the lock froze at its one-time 2026-07-28 seed and
has now crossed ABANDONED_CODE_COMMIT_THRESHOLD (200 commits touching
src/frob/**/*.py since the stamp), tripping gate:DEPR DEPR006
"deprecated-baseline lock producer looks ABANDONED". The DEPR005 content
check still passes against the frozen set; only the DEPR006 abandonment
signal fires.

Decide and implement one of:
1. Wire the producer into land: rebuild the `current` dict via
   deprecated_current_references over all frob:deprecated symbols at land
   time, then call save_deprecated_baseline so the lock re-stamps on every
   land (or on a cadence).
2. Retire the DEPR005/DEPR006 machinery entirely if the baseline check is
   not worth maintaining a production producer for.

A pin was added to frob-deprecated-baseline.lock.json's top-level "pin" key
(sibling ticket, see its ticket body) as the interim mask that silences
DEPR006 while this ticket is open. That pin should be removed once this
ticket lands a real fix (either the producer wiring or the retirement).
