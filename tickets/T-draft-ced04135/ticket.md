---
id: T-draft-ced04135
title: Wire DSTACK001 into gates dispatch, TIER_A_HANDLERS, and frob.toml threshold
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
- frob.toml
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
found while working T-4713: frob.gates._directive_stack.stack_lint_violations (DSTACK001) and frob.gates._fix_engine_text.fix_dstack001_merge exist and are tested, but are not yet called from anywhere -- run_gates in gates/__init__.py never collects stack_lint_violations into the violation set, and TIER_A_HANDLERS in _fix_engine.py never registers fix_dstack001_merge. Both files were outside T-4713's declared scope. Also: the stack threshold (default 4) is a Python-level parameter only -- frob.toml wiring was blocked by a lease collision with the concurrently in-progress T-4663 (scope 'frob.toml'); this ticket should add a [tool.frob] (or similar) config key and thread it through.