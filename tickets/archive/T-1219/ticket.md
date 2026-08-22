---
id: T-1219
title: 'perf: migrate tree-extraction layer to frob_core (Rust)'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/**
- frob-core/**
evidence_scope:
- tests/unit/test_extract_native.py
- tests/unit/test_capability_native.py
- tests/unit/test_arch_python_native.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): epic-rollup close: T-1219''s 4 children (T-1220..T-1223)
    already shipped and archived done; this ticket only records the rollup Done report
    and closes the umbrella, no new code'
  actor: logan
  at: '2026-08-18'
  old_length: 6942
  new_length: 7152
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches
- tests/test_vet.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Umbrella epic: migrate the Python-side tree-sitter tree-extraction layer (frob.lang._extract.extract, _walk_python, _common.walk) into frob_core (PyO3/Rust), per the report's Rust-migration-candidates ranking. This is the largest single native-cost family measured (perf 38 pct, clones 69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct -- summed ~40-50s native per full check) and is not covered by frob_core today (existing kernels consume the token lists this layer produces). 4 children: tree-extraction kernel, capability-scan resolver, arch metrics single-pass walk export, and an interim zero-Rust tree-sitter Query step for comment/docstring spans. New FFI boundaries must satisfy FFI001/FFI002 (src/frob/gates/_ffi_boundary.py).