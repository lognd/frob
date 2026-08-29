---
id: T-3392
title: Resolve OPAQUE001 dynamic-key container call in test_land_finish_idempotent
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_finish_idempotent.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: declaration-only fix has no code-behavior defect to reproduce; per BUG002
    remedy (3)
  actor: logan
  at: '2026-08-29'
  old_length: 283
  new_length: 676
evidence:
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OPAQUE001: line 243 uses a runtime-resolved dynamic-key container call the capability scanner cannot statically resolve. Rework to a statically-resolvable call or declare the capability explicitly so the scanner can verify it. Part of PyPI release error-floor burn (Series EQ slice).

frob:waive BUG002 reason="detector-defect ticket, not a code-behavior fix: adds one frob:waive OPAQUE001 comment discharging a lexical false-positive (regex crossing a statement boundary in OPAQUE001's own scanner, filed separately as T-3405); no behavior change to reproduce with a failing-then-passing test. Green run of the containing test confirms the waiver did not alter test outcome."