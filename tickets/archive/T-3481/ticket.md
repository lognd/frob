---
id: T-3481
title: 'frob-core #[pyfunction]s hold the GIL for O(n) work, defeating pytest-timeout
  like T-3457'
state: done
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-core/src/**
- tests/unit/test_frob_core_gil.py
- docs/modules/dup.md
- docs/modules/arch.md
- docs/modules/vet.md
- docs/modules/lang.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/dup.md
  reason: T-3481 GIL-release note required by AFFECT001 for the frob-core kernels
    doc section
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/arch.md
  reason: 'AFFECT001: py_function_metrics doc cross-reference'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/vet.md
  reason: 'AFFECT001: scan_python_capabilities doc cross-reference'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/lang.md
  reason: 'AFFECT001: extract_tree_* doc cross-reference'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS111 fs.write+exec via-list declarations for the new test
    file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: testsuite::fs.write/exec ratchet ceiling bumps required by SELFAUDIT001/SYS111
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_frob_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_near_duplicate_indices
- tests/unit/test_frob_core_gil.py::TestGilActuallyReleased::test_background_thread_runs_during_near_duplicate_indices
- tests/unit/test_frob_core_gil.py::TestResultsUnchanged::test_near_duplicate_indices_result_unchanged
- tests/unit/test_frob_core_gil.py::TestResultsUnchanged::test_resolve_call_edges_result_unchanged
- tests/unit/test_frob_core_gil.py::TestResultsUnchanged::test_r3_canonical_hash_result_unchanged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f21e301c722ba015d94db1d3020dcdb028515274
---
Same mechanism as T-3457 (strata-core); see that ticket and tests/unit/strata/test_strata_core_gil.py for the fix shape and evidence.