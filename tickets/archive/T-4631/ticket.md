---
id: T-4631
title: Clean tests/unit docstrings of change-narrative (DOCARCH001) cluster 4
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
- tests/unit/gates/test_lexical_selfcheck.py
- tests/unit/graph/test_dsl.py
- tests/unit/rapid_sweep_suite/test_baseline.py
- tests/unit/rapid_sweep_suite/test_commit.py
- tests/unit/rapid_sweep_suite/test_dispose.py
- tests/unit/strata/test_audit.py
- tests/unit/strata/test_claims.py
- tests/unit/strata/test_fragments.py
- tests/unit/strata/test_mode_conformance.py
- tests/unit/strata/test_parse.py
- tests/unit/strata/test_strata_core_gil.py
- tests/unit/strata/test_vmodel_authoring.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_artifact_smoke_script.py
- tests/unit/test_check_tool_unavailable.py
- tests/unit/test_claims_and_store_batch6.py
- tests/unit/test_conftest_suite_result_status.py
- tests/unit/test_cycle_runner_doc_waiver_t2598.py
- tests/unit/test_cycle_waiver.py
- tests/unit/test_docs_module.py
- tests/unit/test_doctor_runner_t1276.py
- tests/unit/test_done_report_check_scope.py
- tests/unit/test_dup_cache.py
- tests/unit/test_findings_severity_pinned.py
- tests/unit/test_frob_core_gil.py
- tests/unit/test_gitattributes_crlf_normalization.py
- tests/unit/test_graph_ingest_batching.py
- tests/unit/test_graph_stat_trust_margin.py
- tests/unit/test_land_compose.py
- tests/unit/test_land_sibling_regression.py
- tests/unit/test_land_squash_residue_reclaim.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/unit/gates/test_sys_selfaudit.py
  reason: collides with in-progress T-4615 lease on tests/**/test_sys*.py; deferred,
    noted in why-file
  actor: logan
  at: '2026-09-19'
evidence:
- tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates
designated_repro_test: null
acceptance:
- text: Given a scoped frob check on cluster 4 files, when DOCARCH001 is measured,
    then its finding count for those files is 0
  evidence:
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4419 (166->182 re-measurement, 2026-09-19). Cluster 4: 33 DOCARCH001 findings across 33 files (all weight-1). Rewrite each flagged docstring to state WHAT the test proves, not the change narrative. See T-4419 body for the full per-file breakdown and cluster plan.