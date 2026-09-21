---
id: T-5222
title: 'PLATFORM002 new finding: src/frob/worktrees/_disposable_sweep.py:120 os.kill(pid,0)
  outside sanctioned liveness probe'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/worktrees/_disposable_sweep.py
- src/frob/gates/_win32_kill_signal.py
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
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/gates/test_win32_kill_signal.py::TestPlatform002::test_frob_itself_is_clean fails: src/frob/gates/_win32_kill_signal.py's gate now reports a NEW PLATFORM002 finding at src/frob/worktrees/_disposable_sweep.py:120, os.kill(<pid>, 0) used outside the gate's sanctioned liveness-probe allowlist. Fix: either route this call through the sanctioned liveness-probe helper the gate already recognizes, or waive it with a stated reason if it is genuinely a different, correct use of signal 0 (the gate's own comment at src/frob/gates/_win32_kill_signal.py notes 'genuinely real signal delivery misidentified by this scan' is a known false-positive shape -- confirm which case this is before fixing).