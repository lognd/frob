---
id: T-4421
title: Clean system, scripts, and remaining test docstrings of change-narrative (DOCARCH001)
state: queued
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: T-2994
tier: story
sprint: v0.533.0
runs_last: false
milestone: 0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a full frob check on tests/system, scripts/, and the remaining test
    corpora, when DOCARCH001 is measured, then their combined finding count is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001 measured tests/system 12 + scripts/fleet_status.py 7 + remaining tests ~100 = ~119 findings (owner's estimate ~130) on a full check today (2026-09-11), outside src/frob, tests/unit and the land+gates suites. Rewrite each flagged docstring to state WHAT the symbol/test does. Denominator: ~130 (system+scripts+rest).