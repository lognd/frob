---
id: T-5275
title: Wire FMT002 into gates dispatch and TIER_A_HANDLERS
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_fix_engine.py
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
found while working T-4714: frob.gates._fmt_directives.noqa_strip_violations (FMT002) and frob.gates._fix_engine_text.fix_fmt002_noqa_strip exist and are tested, but are not yet called from anywhere -- run_gates in gates/__init__.py never collects noqa_strip_violations into the violation set, and TIER_A_HANDLERS in _fix_engine.py never registers fix_fmt002_noqa_strip. Both files were outside T-4714's declared scope. Same class of gap as T-draft-ced04135 (DSTACK001's own wiring follow-up, T-4713).