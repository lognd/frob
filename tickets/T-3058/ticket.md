---
id: T-3058
title: 'frob:waive is being used as temporary suppression where frob:debt belongs:
  2117 waivers vs 85 debt, until= at 0%, 767 citing resolved tickets in prose'
state: dropped
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
## Drop reason
- 2026-08-28: Premise already resolved by T-3062 (done): WAIVE009/WAIVE010 gates already discriminate frob:waive reasons reading as deferred/temporary work (until/pending/for now/temporarily/promise phrases) from permanent provenance-style waivers, are wired into run_gates (src/frob/gates/__init__.py:8385,8390), and carry both must-fire and must-stay-quiet fixtures in tests/test_waive_gate.py. Re-measured this drive: 2208 frob:waive vs 93 frob:debt occurrences, matching T-3062's own 2117/85 baseline (same finding, ticket re-filed under a new id after T-3062 already shipped the discrimination this ticket asks for). (absorbed by T-3062)
