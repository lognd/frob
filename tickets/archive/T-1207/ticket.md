---
id: T-1207
title: 'perf: DEPR005 full-repo xref per deprecated symbol -- one per-run index'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/_debt_deprecated.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDeprecatedGate::test_depr005_reference_set_combines_consumers_and_xref
- tests/test_gates.py::test_gates_run_gates_integration
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
designated_repro_test: null
acceptance:
- text: 'GIVEN _depr005_violations currently runs exports_consumers+xref per baselined
    deprecated symbol (8 full-repo scans for 4 symbols today, ~4.5s native/symbol,
    linear growth) WHEN a single per-run index ({identifier -> [(file, line, context)],
    file -> imported-names}) is built once from one repo pass THEN the deprecated
    stage drops from 17.9s toward ~2-3s native and per-symbol cost stops growing linearly
    (report candidate #2)'
  evidence:
  - tests/test_gates.py::TestDeprecatedGate::test_depr005_reference_set_combines_consumers_and_xref
  - tests/test_gates.py::test_gates_run_gates_integration
  - tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
  - tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire
  - tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
threat: null
component: null
---
Root cause: gates/_debt_deprecated.py:596 calls deprecated_current_references per edge -> xref/__init__.py:125 (per-file parse+identifier walk) and exports/__init__.py:188 (second xref per symbol) -- 8 full repo scans for only 4 symbols, ~100 pct of the 17.9s stage. Fix: build one per-run index from a single pass (or from the snapshot + frob_core.referenced_names) and answer all symbols from it, collapsing the exports_consumers/xref double scan. Companion lint rule tracked on the sibling 'perf: PERF01x detectors' ticket: repo-scan API (xref/exports_consumers/iter_files) called inside a loop over symbols.