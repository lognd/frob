---
id: T-3777
title: fix win32 failures in hook-guard test suite
state: in-progress
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
- src/frob/hooks/**
- tests/test_hook_root_write_guard.py
- tests/test_hook_frob_suggest.py
- tests/test_hook_root_cleanliness_detector.py
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
Windows CI failures in hook_root_write_guard (18), hook_frob_suggest (7), hook_root_cleanliness_detector (2). Likely shared root cause: path normalization / shell-command parsing / backslash vs forward-slash in the hook's checkout-path detection. Fix shared cause if present, confirm each via winrun.