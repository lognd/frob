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
- .claude/hooks/_root_write_guard_lib.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/_root_write_guard_lib.py
  reason: escape/tokenization fix in the shared shell-token helper root-write-guard.py
    depends on lives here, not under src/frob/hooks
  actor: logan
  at: '2026-09-04'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS100 env.read capability declaration needs the two new test
    files' os.environ reads added to testsuite's via list
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI failures in hook_root_write_guard (18), hook_frob_suggest (7), hook_root_cleanliness_detector (2). Likely shared root cause: path normalization / shell-command parsing / backslash vs forward-slash in the hook's checkout-path detection. Fix shared cause if present, confirm each via winrun.