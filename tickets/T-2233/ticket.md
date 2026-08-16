---
id: T-2233
title: 'Break vet/ import cycle (WARNING): _hook.py<->_closedworld.py<->_scan_violations.py<->_scan.py<->__init__.py'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: T-2202
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_hook.py
- src/frob/vet/_closedworld.py
- src/frob/vet/_scan_violations.py
- src/frob/vet/_scan.py
- src/frob/vet/__init__.py
- tests/unit/test_vet_cycle_regression.py
evidence_scope:
- tests/unit/test_vet_cycle_regression.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_vet_cycle_regression.py
  reason: new repro/regression test for the import-cycle fix
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
designated_repro_test: tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
acceptance:
- text: Given current main, when 'uv run frob check --only cycle' runs, then the vet/
    cluster (_scan_violations.py, _scan.py, _closedworld.py, _hook.py, vet/__init__.py)
    no longer appears in the WARNING output. This test MUST currently fail (the cluster
    is in today's output).
  evidence:
  - tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
- text: 'MUST-STILL-PASS CONTROL: after the fix, ''uv run frob check --only cycle''
    still reports the gates/lang/graph cluster, the dup/_pipeline cluster, and the
    tickets/app/serve/verify mega-cluster (or their post-fix equivalents) -- fewer
    TOTAL clusters than before this leaf''s fix means the detector was narrowed, not
    the cycle fixed, and must be rejected.'
  evidence:
  - tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
- text: Determine the exact closing edge with resolve_local_import/'frob explore xref'
    before editing (token/grammar reasoning, not text search). Likely the same package-namespace-vs-leaf-submodule
    pattern as T-2232 (vet/__init__.py re-exporting from _scan.py/_scan_violations.py
    while one of the leaf modules imports back through 'from frob.vet import X' instead
    of the leaf file) -- confirm before assuming; this is WARNING severity (4-node
    cycle, not the error-severity 5-node clusters) so it may also be a simple 2-file
    mutual-helper split fixable by extracting a shared _models-style module.
  evidence:
  - tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
threat: null
component: null
anchor: false
anchor_reason: null
---
Leaf of T-2202 (epic). Measured directly from 'uv run frob check --only cycle' on 2026-08-16; matches T-2202's originally recorded Leaf 4 description closely (vet/ only: _hook.py, _closedworld.py, _scan_violations.py, _scan.py, __init__.py) -- this cluster did not grow since filing, unlike the other three.