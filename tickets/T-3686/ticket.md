---
id: T-3686
title: fix win32 CTRL_C injection from os.kill(pid,0) in admission pid-liveness probe
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
- src/frob/check/__init__.py
- tests/unit/test_check_admission.py
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
T-3683 bisected the win32 injected-SIGINT to the admission-budget acquisition window (stop-before 'admission' is DIRTY, 'console-scope' is CLEAN). Root cause: _pid_alive() calls os.kill(pid, 0) to probe liveness (T-3256/T-3287's registry reaping in _live_concurrent_checks). On win32, CPython's os.kill maps signal 0 to CTRL_C_EVENT (numeric value 0) and implements it via GenerateConsoleCtrlEvent, which broadcasts Ctrl+C to the whole console process group -- including the calling frob check process itself and any subprocess test runners sharing its console. This fires exactly when _live_concurrent_checks reaps stale/sibling markers during admission, matching the bisection window precisely. Fix: make _pid_alive win32-safe (do not call os.kill with signal 0 on win32; use OpenProcess/CloseHandle via ctypes to probe existence without touching console-ctrl state). References T-3648, T-3256, T-3287, T-3675.