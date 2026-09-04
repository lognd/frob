---
id: T-3751
title: 'win32 test portability (fcntl class): tests importing fcntl fail on Windows;
  skipif POSIX-only lock tests'
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
- tests/test_coverage_wait_shared.py
- tests/test_serve_socket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: these tests simulate the Windows msvcrt lock backend on POSIX via real fcntl.flock;
    on real Windows they must skipif since the real msvcrt backend runs instead
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/test_serve_socket.py
  reason: these tests simulate the Windows msvcrt lock backend on POSIX via real fcntl.flock;
    on real Windows they must skipif since the real msvcrt backend runs instead
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
