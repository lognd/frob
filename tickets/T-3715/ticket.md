---
id: T-3715
title: vet hook exits blocking in advisory-only mode
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
apollo FROBLEMS.md 2026-09-03: the vet hook printed 'advisory-only mode' (no [vet] section existed yet) but still exited 2 and blocked the install. Advisory mode that blocks is not advisory; with no [vet]/[vet.allow] config the hook should warn and exit 0.