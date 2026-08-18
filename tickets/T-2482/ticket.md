---
id: T-2482
title: Declare fs.read/fs.write/exec for T-2467's waive-audit module+tests (SELFAUDIT001
  SYS100)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
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
T-2467's land (7f8193fc958ef608da902730128c6278347b3355) introduced new
SELFAUDIT001 SYS100 (declared-but-not-observed's inverse: observed-but-
not-declared) findings because design/frob.strata was outside T-2467's
declared scope, so its new fs.read/fs.write/exec observations were never
declared. Measured directly post-land:

  gates: fs.read at src/frob/gates/_waive_audit_watermark.py:110
  gates: fs.write at src/frob/gates/_waive_audit_watermark.py:138
  testsuite: exec at tests/unit/test_waive_audit_runner.py:28,29,35,39,40,88
  testsuite: fs.write at tests/unit/test_waive_audit_runner.py:44,73
  testsuite: fs.write at tests/unit/test_waive_audit_watermark.py:26

All genuine (subprocess.run calls in the test git-fixture helpers, real
.open()/.write_text() calls in the watermark module) -- declare them,
following the same via-list-addition pattern as every prior T-2390/T-2457/
T-2463/T-2465 SELFAUDIT001 fix.
