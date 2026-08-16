---
id: T-2232
title: 'Break dup/_pipeline<->dup/__init__ import cycle: submodules resolve _cache/_core
  through the package namespace instead of the leaf module'
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
- src/frob/dup/_pipeline/_fingerprint.py
- src/frob/dup/_pipeline/_probe.py
- src/frob/dup/_pipeline/_smt.py
- src/frob/dup/_pipeline/_callgraph.py
- src/frob/dup/_pipeline/__init__.py
- src/frob/dup/_template.py
- src/frob/dup/__init__.py
- tests/unit/test_dup_pipeline_cycle_regression.py
evidence_scope:
- tests/unit/test_dup_pipeline_cycle_regression.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_dup_pipeline_cycle_regression.py
  reason: new repro/regression test for the import-cycle fix
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle
designated_repro_test: tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle
acceptance:
- text: Given current main, when 'uv run frob check --only cycle' runs, then the dup/_pipeline
    cluster (_fingerprint.py, _probe.py, _smt.py, _callgraph.py, _pipeline/__init__.py,
    _template.py, dup/__init__.py) no longer appears in the FAIL output. This test
    MUST currently fail (the cluster is in today's output).
  evidence:
  - tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle
- text: 'MUST-STILL-PASS CONTROL: after the fix, ''uv run frob check --only cycle''
    still reports the gates/lang/graph cluster, the vet warning cluster, and the tickets/app/serve/verify
    mega-cluster (or their post-fix equivalents) -- fewer TOTAL clusters than before
    this leaf''s fix means the detector was narrowed, not the cycle fixed, and must
    be rejected.'
  evidence:
  - tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle
- text: 'MECHANICAL FIX outline: ''from frob.dup import _cache, _core'' in _fingerprint.py
    (and the equivalent ''from frob.dup import _core'' in _template.py) resolves through
    frob/dup/__init__.py''s namespace even though _cache.py and _core.py are leaf
    submodules that import nothing back from dup/_pipeline/. Re-target these imports
    at the leaf submodules directly (e.g. ''from frob.dup._cache import get_fingerprint,
    get_verdict, put_fingerprint, put_verdict'' and ''from frob.dup._core import anti_unify,
    core_available'') so the static import edge lands on _cache.py/_core.py, not on
    dup/__init__.py''s own import of _pipeline/_template. Verify with resolve_local_import
    (or ''frob explore xref'') which exact statement closes the cycle before editing
    -- token/grammar reasoning, not text search, per standing directive.'
  evidence:
  - tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle
threat: null
component: null
anchor: false
anchor_reason: null
---
Leaf of T-2202 (epic). Measured directly from 'uv run frob check --only cycle' on 2026-08-16; today's cluster (7 files) is LARGER than T-2202's originally recorded 4-file tickets/-style description for this cluster ('dup/ only: _pipeline/_smt.py, _template.py, _pipeline/_fingerprint.py, _pipeline/_callgraph.py') -- it now also includes _probe.py, _pipeline/__init__.py, and dup/__init__.py. Attributable to T-2211 (landed after T-2202 was filed), which fixed resolve_local_import to stop dropping imported names for the 'from X import submodule' idiom used throughout this cluster. Not a regression; do not revert anything.