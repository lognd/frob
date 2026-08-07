---
id: T-1110
title: 'warnings: DEAD001/COV/REF edge burn-down (DEAD 32, COV 10, REF 10 unwaived)'
state: done
kind: bug
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
- invariants/**
- strata-core/src/parse/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: invariants/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
- op: add
  glob: strata-core/src/parse/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
- op: add
  glob: invariants/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
- op: add
  glob: strata-core/src/parse/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_none_for_top_level_function
- tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method
- tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check WHEN the dead/coverage/refs gates run THEN DEAD001,
    COV00x, and REF00x report zero unwaived warnings, each finding either root-fixed
    (dead code removed, edge bound) or waived with a grounded reason
  evidence:
  - tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_none_for_top_level_function
  - tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method
  - tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires
  - tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
Post-wave-16 residue: 32 DEAD001 dead-symbol warnings, 10 COV coverage-edge warnings, 10 REF reference warnings (unwaived, per gate summary). T-1024 precedent: DEAD001 13->0 and COV006 3->0 via real removals and edge bindings, not blanket waivers. Callgraph blind spots (cross-package privates, indexed-constant mutation) get confirmed-exercised waivers per the 3d574f3a precedent. Narrow scope to the real finding sites at start.