---
id: T-4418
title: Clean src/frob docstrings of change-narrative (DOCARCH001)
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
- text: Given a full frob check on src/frob, when DOCARCH001 is measured, then its
    finding count for src/frob is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001 measured 146 findings in src/frob on a full check today (2026-09-11). Rewrite each flagged docstring to state WHAT the symbol does, not the change history/ticket narrative behind it; move any narrative worth keeping into the ticket that made the change. Denominator: 146 (src/frob).