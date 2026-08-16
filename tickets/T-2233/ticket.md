---
id: T-2233
title: 'Break vet/ import cycle (WARNING): _hook.py<->_closedworld.py<->_scan_violations.py<->_scan.py<->__init__.py'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given current main, when 'uv run frob check --only cycle' runs, then the vet/
    cluster (_scan_violations.py, _scan.py, _closedworld.py, _hook.py, vet/__init__.py)
    no longer appears in the WARNING output. This test MUST currently fail (the cluster
    is in today's output).
  evidence: []
- text: 'MUST-STILL-PASS CONTROL: after the fix, ''uv run frob check --only cycle''
    still reports the gates/lang/graph cluster, the dup/_pipeline cluster, and the
    tickets/app/serve/verify mega-cluster (or their post-fix equivalents) -- fewer
    TOTAL clusters than before this leaf''s fix means the detector was narrowed, not
    the cycle fixed, and must be rejected.'
  evidence: []
- text: Determine the exact closing edge with resolve_local_import/'frob explore xref'
    before editing (token/grammar reasoning, not text search). Likely the same package-namespace-vs-leaf-submodule
    pattern as T-2232 (vet/__init__.py re-exporting from _scan.py/_scan_violations.py
    while one of the leaf modules imports back through 'from frob.vet import X' instead
    of the leaf file) -- confirm before assuming; this is WARNING severity (4-node
    cycle, not the error-severity 5-node clusters) so it may also be a simple 2-file
    mutual-helper split fixable by extracting a shared _models-style module.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Leaf of T-2202 (epic). Measured directly from 'uv run frob check --only cycle' on 2026-08-16; matches T-2202's originally recorded Leaf 4 description closely (vet/ only: _hook.py, _closedworld.py, _scan_violations.py, _scan.py, __init__.py) -- this cluster did not grow since filing, unlike the other three.