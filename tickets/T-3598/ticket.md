---
id: T-3598
title: 'ARCH103 waiver-stays-effective regression: waived function no longer fires
  raw on refactor/_verify.py'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch
- src/frob/refactor/_verify.py
- tests/unit/test_arch_srp.py
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
run 33412543005, HEAD 2bb9c46ea: on both ubuntu and macOS the ONLY suite failure is tests/unit/test_arch_srp.py::TestArch103WaiverStaysEffective::test_import_check_env_arch103_is_waived -- AssertionError: expected ARCH103 to still fire raw on refactor/_verify.py::_import_check_env. That test (from T-3395) asserts the waiver stays effective by checking ARCH103 still fires raw there; something in recent lands stopped ARCH103 firing raw on that function (candidates: an ARCH103 detector change, a refactor of _import_check_env dropping its decision-point count below threshold, or a waiver-family change from T-3581/T-3575). Investigate with git log --oneline -20 -- src/frob/arch src/frob/refactor/_verify.py src/frob/gates/_waive.py and fix the right side: if the function genuinely dropped below ARCH103's threshold, the waiver is dead weight -- remove the waiver AND update the test to assert the new reality; if the detector regressed, fix the detector.