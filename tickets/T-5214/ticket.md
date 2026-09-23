---
id: T-5214
title: design/frob.strata narrative node missing declarations for frob.narrative._bulk
  (SYS003+SELFAUDIT001 cascade)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
blocked_by:
- T-4113
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations (and its shared frob_self_scan_artifacts fixture cascading into test_conform_eval_needle.py, test_mutation_audit.py, test_selfconform.py, test_sys003_calibration.py) fail with 8 real SYS/SELFAUDIT violations, all rooted in src/frob/narrative/_bulk.py (a module already present in design/frob.strata's narrative node's code glob and may fs.read/fs.write grants, line ~1073-1084) never getting its interface/flow declarations updated when it was added: (1) SYS003 undeclared cross-component import frob.gates._narrative_blocks at src/frob/narrative/_bulk.py:37 (narrative -> gates) -- design/frob.strata only declares the REVERSE flow f_t3029_gates_narrative (gates -> narrative, line ~2293); a narrative -> gates flow is now also needed. (2) SELFAUDIT001 SYS100 node=testsuite: capability 'html_render' observed but not declared. (3) SELFAUDIT001 SYS110 node=narrative: six public symbols (BulkItem, BulkPlan, apply_bulk, discover_targets, find_blocks, plan_bulk) are public in code but missing from the narrative node's interface= declaration. Fix: add the missing flow + interface= entries (and the testsuite html_render capability) to design/frob.strata; confirm with tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations.