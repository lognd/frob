---
id: T-3714
title: vet --hook vets whole resolution instead of delta
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
- src/frob/vet/_hook.py
- src/frob/vet/_scan.py
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
apollo FROBLEMS.md 2026-09-03: frob vet --hook 'uv add tinycss2' blocked on uv@0.12.9 and build@1.6.0, neither in tinycss2's dependency closure (tinycss2 -> webencodings only). The hook appears to vet the whole prospective resolution / tool universe rather than the delta the command introduces, so any fresh release of unrelated tooling blocks every install command.