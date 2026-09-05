---
id: T-3796
title: fix mutate line-range scoping CRLF handling on win32
state: done
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
- tests/test_mutate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/mutate/__init__.py tests/test_mutate.py
  reason: split single-string scope into a valid glob
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_mutate.py
  reason: split single-string scope into a valid glob
  actor: logan
  at: '2026-09-05'
body_changes:
- mode: append
  reason: 'waive BUG002: win32-only bare-python interpreter mismatch, no linux repro
    possible'
  actor: logan
  at: '2026-09-05'
  old_length: 242
  new_length: 340
evidence:
- tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak
- tests/test_mutate.py::test_run_mutations_line_ranges_scopes_to_changed_lines
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
test_run_mutations_line_ranges_scopes_to_changed_lines and test_run_mutations_survivors_when_tests_weak fail on win32; investigate CRLF/newline handling in mutate line-range computation vs subprocess pytest invocation. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; no Linux parent-commit repro"