---
id: T-draft-3753ba68
title: 'SQL/LAUNCH tool-family landing incomplete: REG008 enforces edges, doctor double-finding,
  exports, runtime_deps'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- docs/design/registry/check-coverage.yaml
- src/frob/doctor.py
- src/frob/sql/_sqlfluff_plugin.py
- tests/test_check_coverage_registry.py
- tests/test_registry_exhaustiveness.py
- tests/unit/test_doctor.py
- tests/unit/test_exports.py
- tests/unit/test_runtime_deps.py
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
Found while draining CI run 36173008509 (dev 473cee7656). Reproduces on
ubuntu-latest and macos-latest (both legs, Test step).

The SQL/LAUNCH tool-family feature (sqlfluff plugin, SQL1xx/LAUNCH1xx rules,
doctor.family_required_tool_findings) landed with several loose ends:

1. REG008 (36 hits): docs/design/registry/check-coverage.yaml entries for
   CHK-GATE-SQL123..SQL130 and CHK-GATE-LAUNCH101..LAUNCH107 are dispositioned
   handled_by:<RULE> but no `frob:enforces <id>` edge exists anywhere in code.
   FAILED tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
   FAILED tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
   FAILED tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules - assert 666 == 664

2. tests/unit/test_doctor.py::TestFamilyRequiredToolFindings::test_sql_relevant_missing_sqlfluff_is_a_finding - assert 2 == 1
   doctor.family_required_tool_findings now emits 2 findings where the test
   expects 1 -- likely a duplicate/second finding path added by the feature.

3. tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
   frob-exports still reports missing symbols:
   {'src/frob': ['frob.doctor.family_required_tool_findings', 'frob.doctor.FamilyToolFinding']}
   -- the new doctor symbols are not wired into the package's exports policy.

4. tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_every_unguarded_third_party_import_is_declared
   import name(s) absent from _DIST_FOR_IMPORT: {'sqlfluff': {'src/frob/sql/_sqlfluff_plugin.py'}}
   -- src/frob/sql/_sqlfluff_plugin.py imports sqlfluff unguarded but the
   runtime-deps declaration table was never updated.

Proposed fix: finish the landing -- add the missing frob:enforces edges (or
re-disposition the registry entries), fix the doubled doctor finding, export
the two new doctor symbols, and add the sqlfluff dist-name table entry.
Scope spans registry data, doctor, exports policy and runtime-deps table --
too broad for a single small patch, filing for a dedicated pass.
