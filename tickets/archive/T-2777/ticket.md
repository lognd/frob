---
id: T-2777
title: Reformat batch 3 of ruff-format-only reformat (T-2359 child)
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_inv.py
- src/frob/gates/_lang_conformance.py
- src/frob/gates/_refs.py
- src/frob/gates/_sys.py
- src/frob/gates/_sys_selfaudit.py
- src/frob/gates/_toplevel_scalar_schema.py
- docs/modules/lang.md
evidence_scope:
- tests/test_gates_fix_engine.py
- tests/test_lang_conformance_gate.py
- tests/test_refs_gate.py
- tests/gates/test_rule_id_scan_branches.py
- tests/test_gates.py
- tests/unit/test_profile_table_schema.py
- tests/unit/test_testing_table_schema.py
- tests/unit/test_toplevel_scalar_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_tickets_gate.py
  reason: T-2557 holds a live cross-worktree lease on this file; excluded to avoid
    collision
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_waive.py
  reason: T-2557 holds a live cross-worktree lease on this file; excluded to avoid
    collision
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_profile_schema.py
  reason: AFFECT001 closure doc docs/modules/gates.md is leased live by T-2557; deferring
    these files to a later batch
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_rule_id_scan.py
  reason: AFFECT001 closure doc docs/modules/gates.md is leased live by T-2557; deferring
    these files to a later batch
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_testing_schema.py
  reason: AFFECT001 closure doc docs/modules/gates.md is leased live by T-2557; deferring
    these files to a later batch
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/lang.md
  reason: 'AFFECT001: format-only digest move on capability_conformance_gate requires
    acking its affects()-closure doc'
  actor: logan
  at: '2026-08-21'
evidence:
- tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_merge_introduced_targeted_format_applies
- tests/test_lang_conformance_gate.py::TestLangConformanceGate::test_real_registry_is_clean
- tests/test_refs_gate.py::TestTiers::test_two_refs_passes
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
- tests/test_gates.py::TestSysGate::test_sys001_valid
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_clean_model_no_violations
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_testing_known_keys_reads_test_policy_model_fields
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_now_fire_reports_the_undeclared_key
designated_repro_test: null
acceptance:
- text: given the batch-3 files, when ruff format --check runs on them, then zero
    need reformatting
  evidence:
  - tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_merge_introduced_targeted_format_applies
  - tests/test_lang_conformance_gate.py::TestLangConformanceGate::test_real_registry_is_clean
  - tests/test_refs_gate.py::TestTiers::test_two_refs_passes
  - tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
  - tests/test_gates.py::TestSysGate::test_sys001_valid
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_clean_model_no_violations
  - tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_now_fire_reports_the_undeclared_key
  - tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_testing_known_keys_reads_test_policy_model_fields
  - tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_now_fire_reports_the_undeclared_key
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c0b92fbd16b15b84fad8765c6879fe1798d01d3a
---
batch 3 of T-2359's ruff-format-only reformat. Format-only, no semantic changes. 12 files: src/frob/gates/_fix_engine_text.py, _inv.py, _lang_conformance.py, _profile_schema.py, _refs.py, _rule_id_scan.py, _sys.py, _sys_selfaudit.py, _testing_schema.py, _tickets_gate.py, _toplevel_scalar_schema.py, _waive.py. Excludes tests/unit/test_ticket_runner_ledger_mirror.py and src/frob/gates/_wire.py out of caution around in-flight T-2770/T-2772 leases.