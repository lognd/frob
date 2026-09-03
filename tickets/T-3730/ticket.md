---
id: T-3730
title: fix win32 failures+hang in test_cli_doctor.py
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
- tests/system/test_cli_doctor.py
- src/frob/doctor.py
- src/frob/app/doctor_runner.py
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
CI run 33721091819 windows job: tests/system/test_cli_doctor.py showed many FAILs (FFFF....FFFFFFFFFFFFFFFFFFFF) then hung at TestDoctorStaleTicketLeases::test_scan_degrades_to_empty_on_a_malformed_ledger. ubuntu+mac pass this file; win32-only. References T-3725 (doctor git-hooks-absent fix just landed), T-3726 (total-budget watchdog that made this visible). Sole remaining Windows CI blocker.