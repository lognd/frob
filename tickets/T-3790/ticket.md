---
id: T-3790
title: fix win32 test_fix_engine scope-lease/tier-a failures
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/fix/*.py tests/gates_suite/test_fix_engine.py
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
win32 CI: tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert and TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content fail. Root cause TBD via winrun. Part of win32 CI drain.