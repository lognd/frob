---
id: T-1338
title: ARCH001 + PERF003 + PERF008 in gates/_debt_deprecated.py
state: done
kind: feature
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_debt_deprecated.py
- tests/test_gates_debt.py
- tests/unit/gates/test_deprecated_baseline.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_debt.py
  reason: 'scope-closure: bound tests for deprecated-debt gate'
  actor: logan
  at: '2026-07-31'
- op: add
  glob: tests/unit/gates/test_deprecated_baseline.py
  reason: T-1338 added a regression test in this file for the PERF008 index-hoist
    fix
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_two_baselined_symbols_each_evaluated_independently
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
- tests/test_gates.py::TestDebtGate::test_clean_debt_produces_no_violations
- tests/test_gates.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations
designated_repro_test: null
acceptance:
- text: given frob check, when gate:ARCH runs, then _depr005_violations is under the
    60-line threshold
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_two_baselined_symbols_each_evaluated_independently
  - tests/test_gates.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations
- text: given frob check, when gate:PERF runs, then _debt_deprecated.py raises 0 PERF003
    and 0 PERF008 findings
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
  - tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
  - tests/test_gates.py::TestDebtGate::test_clean_debt_produces_no_violations
  - tests/test_gates.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations
threat: null
component: gates
---
Three co-located errors: ARCH001 _depr005_violations 74/60 lines (line 644), PERF003 nested loops with equality compare at line 592 (index the inner collection), PERF008 _build_deprecated_ref_index called inside a loop with loop-invariant args at line 683 (hoist/memoize -- it transitively fs-walks).