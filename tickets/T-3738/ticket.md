---
id: T-3738
title: fix win32 hang in TestWireGate git subprocess calls
state: in-progress
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
- tests/gates_suite/test_wire.py
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
CI run 33739420656 (windows): pytest_timeout watchdog stuck at tests/gates_suite/test_wire.py::TestWireGate::test_wire. TestWireGate's raw subprocess.run git calls (add/commit/checkout) had no timeout=, no GIT_TERMINAL_PROMPT=0, and no -c commit.gpgsign=false on commit -- the exact win32 hang class T-3730/T-3735 fixed in tests/system/test_cli_doctor.py (an inherited global commit.gpgsign=true or credential-helper prompt can block a bare git commit forever with no bound). Bound every subprocess.run in this file the same way.