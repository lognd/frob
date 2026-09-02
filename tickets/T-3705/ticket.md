---
id: T-3705
title: wire win32_kill_signal into a stage group
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/gates/__init__.py
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
T-3696 added PLATFORM002 detector gate win32_kill_signal to _ALL_GATES but not to any _STAGE_GROUPS entry, breaking tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool (ubuntu CI blocker, run 33680767948). Add win32_kill_signal to the same stage group as its sibling PLATFORM gates.