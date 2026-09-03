---
id: T-3689
title: win32 check slow/hangs after T-3686 self-interrupt fix
state: done
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/process/**
- tests/conftest.py
- .github/workflows/ci.yml
- tests/unit/test_check_admission.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-3689 Done report
  actor: logan
  at: '2026-09-02'
  old_length: 82
  new_length: 93
evidence:
- tests/unit/test_check_admission.py::TestTimingDebug::test_disabled_by_default
- tests/unit/test_check_admission.py::TestTimingDebug::test_enabled_when_set_non_empty
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_is_silent_when_disabled
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_prints_breadcrumb_when_enabled
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_elapsed_grows_with_process_start_offset
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3686. See conversation for detail. References T-3686 T-3683 T-3256.

test line