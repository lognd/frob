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
