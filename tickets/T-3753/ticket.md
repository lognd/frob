---
id: T-3753
title: 'win32 test portability (fork/sysconf class): skipif POSIX fork-context and
  os.sysconf tests'
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
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_coverage.py
  reason: only file in the fork/sysconf class actually needing a skipif; the other
    9 assigned files already inline-guard their real os.fork/get_context(fork)/os.sysconf
    usages
  actor: logan
  at: '2026-09-04'
evidence:
- tests/test_coverage.py::TestSpawnWithWatchdog::test_killed_process_group_leaves_no_surviving_children
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
