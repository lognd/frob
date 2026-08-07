---
id: T-1222
title: 'rust: arch python metrics single-pass walk export (extraction only, rules
  stay Python)'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/arch/_python.py
- frob-core/**
- tests/unit/test_arch_python_native.py
- docs/modules/arch.md
- docs/modules/dup.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_arch_python_native.py
  reason: golden-parity test alongside the T-1220/T-1221 precedent's own test file,
    plus the frob:doc anchor for py_function_metrics and dup.md's frob-core kernel
    export count
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/arch.md
  reason: golden-parity test alongside the T-1220/T-1221 precedent's own test file,
    plus the frob:doc anchor for py_function_metrics and dup.md's frob-core kernel
    export count
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/dup.md
  reason: golden-parity test alongside the T-1220/T-1221 precedent's own test file,
    plus the frob:doc anchor for py_function_metrics and dup.md's frob-core kernel
    export count
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring test_arch_python_native.py's fs.write/fs.read
    capabilities on the testsuite node, same as T-1220/T-1221's own precedent
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_control_flow_and_self_field_access
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_flat_function_has_zero_nesting_and_low_cyclomatic
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_function_definition_is_flattened_into_own_entry
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches
designated_repro_test: null
acceptance:
- text: 'GIVEN _run_python_checks is 97 pct of archgate and _py_build_module alone
    is 31 pct, doing body-event/nesting/cyclomatic extraction as separate Python recursions
    per function WHEN a frob_core export py_function_metrics(source: bytes) -> [(span,
    nesting, cyclomatic, events)] replaces the extraction-only portion of _py_build_function/_py_build_module,
    with all rule logic (arch/_lock_ordering.py, _async_hazards.py, _shared_state_race.py,
    _concurrency_model.py, _patterns.py) staying in Python and consuming the exported
    metrics THEN archgate''s per-file walk cost drops toward the export''s native
    cost, and no rule-decision logic crosses the FFI boundary'
  evidence:
  - tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_control_flow_and_self_field_access
  - tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_flat_function_has_zero_nesting_and_low_cyclomatic
  - tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_function_definition_is_flattened_into_own_entry
  - tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches
threat: null
component: null
---
Root cause and target: Rust-migration candidate #3 from the report, MEDIUM feasibility -- more rule logic crosses the boundary than candidates #1/#2, so scope is deliberately extraction-only; keep rule families in Python. frob_core already hosts arch's near-dup clustering (near_duplicate_indices), so the crate boundary for arch already exists and this extends it. FFI001/FFI002 apply. This is independent of Epic A's T-1215 (arch dedupe of _iter_own_scope, a Python-side fix) -- that ticket should land on its own timeline; this ticket does not block or get blocked by it, since T-1215 is a pure-Python fix to the current implementation and this ticket replaces the extraction step underneath it.