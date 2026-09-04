---
id: T-3759
title: pin deprecated-baseline lock to clear DEPR006 abandonment (producer unwired,
  see T-3758)
state: in-progress
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
scope:
- frob-deprecated-baseline.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob-deprecated-baseline.lock.json
  reason: pin escape hatch to clear DEPR006 abandonment
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: set
  reason: record rationale for the pin
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 703
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gate:DEPR fires DEPR006 "deprecated-baseline lock producer looks ABANDONED"
because tighten_deprecated_baseline (the sole writer of
frob-deprecated-baseline.lock.json) has no production call site (see
T-3758) and the lock has been frozen at its 2026-07-28 seed for 1395+
commits touching src/frob/**/*.py, past ABANDONED_CODE_COMMIT_THRESHOLD
(200). Re-stamping is not viable without the producer wiring T-3758
tracks, so this ticket adds the documented pin escape hatch: a top-level
"pin" key on the lock JSON recording why it is pinned and pointing at
T-3758. DEPR005 content check still passes against the frozen baseline;
only the abandonment signal is being silenced, deliberately, pending
T-3758.
