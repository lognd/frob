---
id: T-4629
title: Clean tests/unit docstrings of change-narrative (DOCARCH001) cluster 5
state: done
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: T-4419
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_stage_flip.py
- tests/unit/test_lang_parse_guard.py
- tests/unit/test_logging_quiet.py
- tests/unit/test_memo.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
- tests/unit/test_process_pid_liveness.py
- tests/unit/test_pyfmt_runner.py
- tests/unit/test_rel002_dev_suffix.py
- tests/unit/test_scaffold_natives_shim.py
- tests/unit/test_scaffold_project.py
- tests/unit/test_ticket_new_related.py
- tests/unit/test_waive_audit_watermark.py
- tests/unit/verify/test_backpressure.py
- tests/unit/vet/test_capability_modes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates
designated_repro_test: null
acceptance:
- text: Given a scoped frob check on cluster 5 files, when DOCARCH001 is measured,
    then its finding count for those files is 0
  evidence:
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4419 (166->182 re-measurement, 2026-09-19). Cluster 5: 14 DOCARCH001 findings across 14 files (all weight-1). Includes the 2 leased files DEFERRED from every cluster: tests/unit/verify/test_verify_runner.py (leased T-3082) and tests/unit/strata/test_selfconform.py (leased T-4633) -- pick those up once the leases release. Rewrite each flagged docstring to state WHAT the test proves, not the change narrative. See T-4419 body for the full per-file breakdown and cluster plan.