---
id: T-3794
title: skipif win32 for POSIX-only fs-notify test
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
- tests/test_serve_daemon.py
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
win32 drain: test_fs_change_notifies_the_cached_verify_worker relies on ThreadingUnixStreamServer/AF_UNIX, POSIX-only. Add skipif(win32).