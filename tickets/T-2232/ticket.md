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
land_commit: null
---
Leaf of T-2202 (epic). Measured directly from 'uv run frob check --only cycle' on 2026-08-16; today's cluster (7 files) is LARGER than T-2202's originally recorded 4-file tickets/-style description for this cluster ('dup/ only: _pipeline/_smt.py, _template.py, _pipeline/_fingerprint.py, _pipeline/_callgraph.py') -- it now also includes _probe.py, _pipeline/__init__.py, and dup/__init__.py. Attributable to T-2211 (landed after T-2202 was filed), which fixed resolve_local_import to stop dropping imported names for the 'from X import submodule' idiom used throughout this cluster. Not a regression; do not revert anything.

## Done report

Changed:
  src/frob/dup/_pipeline/_fingerprint.py::_r3_fingerprint (import retarget)
  src/frob/dup/_pipeline/_fingerprint.py::_r4_fingerprint (import retarget)
  src/frob/dup/_pipeline/_fingerprint.py::_r5_fingerprint (import retarget)
  src/frob/dup/_pipeline/_callgraph.py (import retarget, _apted_similarity call site)
  src/frob/dup/_template.py (import retarget, anti_unify call sites)

Diagnosis confirmed before editing: `from frob.dup import _cache, _core` in
_fingerprint.py and `from frob.dup import _core` in _callgraph.py/_template.py
each produce TWO candidate import specifiers per lang/_extract.py's
_python_import_specifiers (T-2211) -- the bare module "frob.dup" AND the
qualified "frob.dup._cache"/"frob.dup._core". resolve_local_import resolves
"frob.dup" to dup/__init__.py, which itself imports _pipeline/_template back
-- that bare-module edge is what closes the cycle, not the qualified one.
Retargeted all three sites to `from frob.dup._cache import ...` /
`from frob.dup._core import ...` so only the leaf-module specifier is ever
emitted.

Evidence: tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle
  (new repro test: runs the real cycle detector -- frob.check._python._build_import_graph
  + frob.cycle.graph.find_cycles -- against this repo's own src/ tree and asserts no
  cycle contains a dup/_pipeline cluster member. FAILED_AT_PARENT confirmed at f9bcbd14e
  (repro-only commit); PASSED after the fix commit b184c1344.)
  Also bound to acceptance[0], acceptance[1] (must-still-pass control), acceptance[2].
  Touched-set: `uv run frob test --base main` -- 39 python outcomes, all PASS.

Manual verification of the must-still-pass control:
  Baseline (before any edit): 3 errors, 1 warning -- gates/lang/graph cluster,
  dup/_pipeline cluster, tickets/app/serve/verify mega-cluster (errors);
  vet cluster (warning); 5 note-severity 2-node clusters.
  After fix: 2 errors, 1 warning -- dup/_pipeline cluster is GONE; the
  gates/lang/graph cluster, the tickets/app/serve/verify mega-cluster, the
  vet warning cluster, and all 5 note-severity clusters are UNCHANGED.
  Full before/after `uv run frob check --only cycle` output captured in
  the worktree session (not committed -- ephemeral verification artifact).

Filed: none (no out-of-scope work found; T-2233 is the planned next ticket
  in this series, not a new discovery)

Gates: frob check --ticket T-2232 to be run at land time; no waivers used.

### Changed
```
 src/frob/dup/_pipeline/_callgraph.py             |  4 +-
 src/frob/dup/_pipeline/_fingerprint.py           | 52 ++++++++++++++----------
 src/frob/dup/_template.py                        |  6 +--
 tests/unit/test_dup_pipeline_cycle_regression.py | 47 +++++++++++++++++++++
 tickets/T-2232/ticket.md                         | 17 +++++---
 5 files changed, 95 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/test_dup_pipeline_cycle_regression.py::TestDupPipelineCycleRegression::test_dup_pipeline_cluster_is_not_a_cycle` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/dup/_pipeline/_fingerprint.py, AFFECT001@src/frob/dup/_template.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2232-t2233/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t2232-t2233/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2232, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
