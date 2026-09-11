---
id: T-4423
title: Promote DOCARCH001/DOC012/NARR001 to error once denominators reach zero
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: medium
blocked_by:
- T-4418
- T-4419
- T-4420
- T-4421
- T-4422
parent: T-2994
tier: ticket
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
- text: Given all five debloat stories closed with zero denominators, when frob.toml
    is checked, then DOCARCH001, DOC012 and NARR001 are severity=error
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001, DOC012 and NARR001 (172 warnings on the last ubuntu CI self-gate) are WARN-tier and non-blocking today, so a green frob check makes no narrative-hygiene claim. Once the five debloat stories (T-4418..T-4422) each measure zero for their denominator, promote DOCARCH001, DOC012 and NARR001 to error severity in frob.toml so the class cannot regress silently.