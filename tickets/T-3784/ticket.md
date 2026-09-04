---
id: T-3784
title: fix win32 DEPR005/cycle-runner path separator mismatches
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
- src/frob/gates/_debt_deprecated.py tests/unit/gates/test_deprecated_baseline.py
- tests/unit/gates/test_deprecated_baseline.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_deprecated_baseline.py
  reason: scope was accidentally a single space-joined glob string; split into two
    proper entries
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: DEPR005 growth-comparison tests fail because _build_deprecated_ref_index keys files with bare str(Path) (backslash-separated on win32) while the baseline lock file stores POSIX-separated keys, so current counts never match baseline counts and DEPR005 spuriously fires on every referencing file. Part of win32 CI drain.