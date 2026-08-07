---
id: T-1208
title: 'perf: strata sys gate ast-parses same 807 files twice (plus a third parse
  elsewhere)'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_code_binding.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_same_component_import_is_fine
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_with_declared_flow_is_fine
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_without_declared_flow_is_a_violation
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_from_import_is_resolved_and_checked
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_level1_relative_import_same_package_is_fine
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_level2_relative_import_crossing_component_is_flagged
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106
designated_repro_test: null
acceptance:
- text: 'GIVEN _reachable_local_files (_selfconform.py:1096) and check_import_conformance
    (_code_binding.py:425) each independently ast.parse+ast.walk the same 807 python
    files (builtins.compile x2421 = 3 parses/file) WHEN a (path, content-hash) ->
    [(spec, line)] import-spec memo is shared for the run (or persisted alongside
    symbols in cache.db), and the two per-node helper calls in the walk collapse into
    one isinstance(Import/ImportFrom) filter THEN sys drops ~5-7s native (report candidate
    #3, currently 23 pct + 23 pct of the sys profile)'
  evidence:
  - tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_same_component_import_is_fine
  - tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_with_declared_flow_is_fine
  - tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_without_declared_flow_is_a_violation
  - tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_from_import_is_resolved_and_checked
  - tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_level1_relative_import_same_package_is_fine
  - tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_level2_relative_import_crossing_component_is_flagged
  - tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
  - tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106
  - tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106
threat: null
component: null
---
Root cause: _selfconform.py:1079 _python_imports_with_lines_module and _code_binding.py:285 _python_imports_with_lines each do a full ast.parse+ast.walk of the same 807 files inside one sys run, and the walk itself calls two Python helpers per node (2.25M nodes). Fix: memoize (path, content-hash) -> [(spec, line)] for the run; replace the two per-node helper calls with one isinstance filter.