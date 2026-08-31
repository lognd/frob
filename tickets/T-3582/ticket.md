---
id: T-3582
title: 'Windows round 5: KeyboardInterrupt survives T-3577''s fix at collection pos
  ~130 (tests/integration)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/integration/**
- tests/conftest.py
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
Run 33385515507, HEAD 94931dde1: windows-latest still dies with KeyboardInterrupt at [1%] despite T-3577's bounded msvcrt lock + bounded run() wrapper in tests/system/conftest.py. Two-part fix: (a) re-add -v --full-trace to the windows-latest Test step in .github/workflows/ci.yml as a PERSISTENT setting while the leg is advisory (comment: stays until Windows is green -- the T-3560 revert was premature given the interrupt survived); (b) serial collection position ~130 falls in tests/integration/ (test_gitlog.py area), NOT tests/system/ -- T-3577's bounded-communicate/taskkill wrapper only fixed tests/system/conftest.py. Survey every subprocess helper the first ~200 collection positions use (tests/integration conftest or per-file helpers, tests/gates helpers, anything invoking frob/git with capture) and apply the same win32-bounded shape (or route them all through the one fixed run() helper -- prefer one home).