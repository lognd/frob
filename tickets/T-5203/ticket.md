---
id: T-5203
title: register VET012 in _KNOWN_GATE_RULES and _osv.py's fetch_url edge in design/frob.strata
state: queued
kind: invariant
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- design/frob.strata
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
T-5138 added VET012 (advisory data unavailable) as a real fired rule id in src/frob/vet/_scan.py, and rewired _osv.py from an osv-scanner subprocess to a direct urllib fetch_url call. Both src/frob/gates/_waive.py (_KNOWN_GATE_RULES, VET001-011 block) and design/frob.strata (the src/frob/vet/** node's 'may fetch_url via' edge, currently only _nvd.py/_registry.py) need updating, but both files were held by T-5121's in-progress lease at T-5138's close-out time so this ticket could not touch them -- see T-5138's Done report.