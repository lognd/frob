---
id: T-0364
title: 'dup: triage 64 duplicate groups into extraction candidates vs false pairs'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: preserve change-narrative removed from git()'s docstring for DOCARCH001
  actor: logan
  at: '2026-09-19'
  old_length: 532
  new_length: 761
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map
- tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks
- tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes
- tests/gates_suite/test_coverage.py::test_gates_run_gates_integration
- tests/test_graph.py::test_graph_build_lock_drift_integration
- tests/unit/strata/test_litmus_pii.py::TestPiiVulnLitmus::test_vuln_pii003_names_the_store
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_declared_retention_discharges
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_no_pii_no_finding
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_pii_with_no_retention_or_erasure_fires_pii003
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_revocation_edge_discharges
- tests/unit/test_check.py::test_check_run_check_arch_integration
- tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_unwaived_group_still_counts
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0204 family 6: frob-dup reports 64 duplicate groups. Triage each into (a) a real extraction candidate -- feed into T-0187's extraction tree, or (b) a false pair -- disposition with a written reason (structural coincidence, distinct semantics, etc.), waived accordingly. NO blanket waiver. Cross-reference T-0187 (dup bleeding-edge work in progress) before duplicating extraction effort. Acceptance: every one of the 64 groups has an explicit disposition (extracted, ticketed under T-0187, or reasoned waiver); honest summary line.



## Docstring narrative preserved (T-4421 debloat, 2026-09-19)

tests/system/conftest.py::git was extracted from four system test modules
that had copy-pasted the same 'run a git subcommand, raise on nonzero exit'
body inline.