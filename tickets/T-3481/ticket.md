---
id: T-3481
title: 'frob-core #[pyfunction]s hold the GIL for O(n) work, defeating pytest-timeout
  like T-3457'
state: in-progress
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Same mechanism as T-3457 (strata-core); see that ticket and tests/unit/strata/test_strata_core_gil.py for the fix shape and evidence.