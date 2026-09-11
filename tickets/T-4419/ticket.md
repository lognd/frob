---
id: T-4419
title: Clean tests/unit docstrings of change-narrative (DOCARCH001)
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
- text: Given a full frob check on tests/unit, when DOCARCH001 is measured, then its
    finding count for tests/unit is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001 measured 166 findings in tests/unit on a full check today (2026-09-11). Rewrite each flagged docstring to state WHAT the test verifies, not the ticket/change narrative behind it. Denominator: 166 (tests/unit).