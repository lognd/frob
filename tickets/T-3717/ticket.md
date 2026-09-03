---
id: T-3717
title: VET004 high-entropy heuristic false-positives on common packages, unreachable
  clean state
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_typosquat.py
- src/frob/check
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
apollo FROBLEMS.md 2026-09-03: VET004 'high-entropy-string' fires on legit packages (webencodings, tomli, typing-inspection, pytest-cov, tinycss2, typani). Docs say VET004 is 'never declarable' so a clean frob vet is UNREACHABLE for repos hitting these false positives through no fault of their own. Also note: frob check does not include vet, so gates stay green while frob vet stays permanently red -- this coupling gap should be tracked alongside the heuristic fix.