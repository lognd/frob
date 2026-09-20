---
id: T-4630
title: Clean tests/unit docstrings of change-narrative (DOCARCH001) cluster 2
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
- tests/unit/test_process_lock.py
- tests/unit/coordinator_suite/test_fleet_report.py
- tests/unit/gates/test_deprecated_baseline.py
- tests/unit/gates/test_wire001_cli_dest_semantic.py
- tests/unit/perf/test_hotpath_smells.py
- tests/unit/rapid_sweep_suite/test_attribution.py
- tests/unit/strata/test_contention.py
- tests/unit/strata/test_cve_fingerprint.py
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_facts.py
- tests/unit/strata/test_native_staleness.py
- tests/unit/test_arch_srp.py
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_dup_legacy_cpp.py
- tests/unit/test_gitattributes_merge.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/unit/test_cli_group_parity.py
  reason: leased by in-progress T-draft-5658939f (cli-regrouping parity fix); deferred,
    pick up once that lease releases
  actor: logan
  at: '2026-09-19'
evidence:
- tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns
- tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_bare_ticket_reference_stays_quiet
designated_repro_test: null
acceptance:
- text: Given a scoped frob check on cluster 2 files, when DOCARCH001 is measured,
    then its finding count for those files is 0
  evidence:
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_bare_ticket_reference_stays_quiet
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4419 (166->182 re-measurement, 2026-09-19). Cluster 2: 33 DOCARCH001 findings across 16 files. Rewrite each flagged docstring to state WHAT the test proves, not the change narrative. See T-4419 body for the full per-file breakdown and cluster plan.