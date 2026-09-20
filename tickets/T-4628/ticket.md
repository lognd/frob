---
id: T-4628
title: Clean tests/unit docstrings of change-narrative (DOCARCH001) cluster 3
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: T-4419
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
- tests/unit/test_land_in_progress_window.py
- tests/unit/test_land_verify_claim_divergence_sentinel.py
- tests/unit/test_lang_strata.py
- tests/unit/test_main_entry.py
- tests/unit/test_policy_weakening_gate.py
- tests/unit/test_process_reap.py
- tests/unit/test_release_workflow_gate.py
- tests/unit/test_skills_sync.py
- tests/unit/test_ticket_runner_land_release.py
- tests/unit/test_unlanded_branch_work.py
- tests/unit/verify/test_worker.py
- tests/unit/arch_suite/test_concurrency.py
- tests/unit/arch_suite/test_dispatch.py
- tests/unit/arch_suite/test_lang_adapters.py
- tests/unit/coordinator_suite/test_fleet_host_load.py
- tests/unit/coordinator_suite/test_fleet_land.py
- tests/unit/gates/test_detector_scope.py
- tests/unit/gates/test_examined_sites.py
- tests/unit/gates/test_exhaustive_handling_path_shape.py
- tests/unit/gates/test_ffi_boundary_path_shape.py
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
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given a scoped frob check on cluster 3 files, when DOCARCH001 is measured,
    then its finding count for those files is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4419 (166->182 re-measurement, 2026-09-19). Cluster 3: 33 DOCARCH001 findings across 21 files. Rewrite each flagged docstring to state WHAT the test proves, not the change narrative. See T-4419 body for the full per-file breakdown and cluster plan.