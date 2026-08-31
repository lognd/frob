---
id: T-3555
title: 'SYS111/SYS100: declare capabilities for the T-3516/T-3526 test files'
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
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
MEASURED run 33361224273 (HEAD 8d4c18055): tests/system/test_frob_self_model.py::test_sys_gate_zero_violations fails -- SYS111 (via THREAT004) reports fs.write via-list on testsuite grew to 41... (undeclared growth). New test files from recent lands (T-3526's tests/unit/test_fix_engine_journal.py and/or T-3516's crash-report tests) need real design/frob.strata declarations for their observed capability sites, plus a capability-via-ratchet.lock.json bump with a measured reason -- the T-3465/T-3484 pattern. Run TestRealGateGreen locally and declare exactly what it lists; do not blanket-grant beyond the measured sites.