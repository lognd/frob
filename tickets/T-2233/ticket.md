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
land_commit: null
---
Leaf of T-2202 (epic). Measured directly from 'uv run frob check --only cycle' on 2026-08-16; matches T-2202's originally recorded Leaf 4 description closely (vet/ only: _hook.py, _closedworld.py, _scan_violations.py, _scan.py, __init__.py) -- this cluster did not grow since filing, unlike the other three.

## Done report

Changed:
  src/frob/vet/_hook.py (import retarget: _registry, _typosquat)
  src/frob/vet/_closedworld.py (import retarget: _cache, _capability, _source)
  src/frob/vet/_scan_violations.py (import retarget: _cache, _registry)
  src/frob/vet/_scan.py (import retarget: _cache, _capability, _ecosystem,
    _lifecycle, _obfuscation, _osv, _source, _supplychain, _typosquat)
  tests/test_vet.py::TestQuarantine.test_fresh_package_blocked (mock target fix)
  tests/test_vet.py::TestQuarantine.test_old_package_ok (mock target fix)
  tests/test_vet.py::TestQuarantine.test_network_failure_degrades_to_unverified (mock target fix)
  tests/test_vet.py::TestQuarantine.test_typosquat_name_blocked_before_any_registry_lookup (mock target fix)

Diagnosis confirmed before editing (same shape as T-2232, per the planner's
"confirm before assuming" note -- confirmed, not assumed): `_hook.py`,
`_closedworld.py`, `_scan_violations.py`, and `_scan.py` each import their
leaf sibling submodules (`_registry`, `_typosquat`, `_cache`, `_capability`,
`_source`, `_ecosystem`, `_lifecycle`, `_obfuscation`, `_osv`,
`_supplychain`) via `from frob.vet import X[, Y, ...]` -- through the
`frob.vet` package namespace, whose own `__init__.py` eagerly imports
`_closedworld`/`_hook`/`_scan` back. lang/_extract.py's
_python_import_specifiers (T-2211) emits both the bare "frob.vet" and the
qualified "frob.vet._registry" specifiers per such import; resolve_local_import
resolves the bare one to vet/__init__.py, closing the cycle -- identical
mechanism to T-2232's dup/_pipeline cluster, just a different package.
Retargeted every site to `from frob.vet._X import name1, name2, ...` (all
needed names are already in each leaf module's __all__).

Second-order effect caught and fixed (per the standing mock.patch caution):
tests/test_vet.py::TestQuarantine's four cases patched
`frob.vet._registry`'s module attribute `_fetch_publish_date` -- after the
retarget, `_hook.py::check_package`'s call site binds its own local name at
import time, so the module-attribute patch stopped taking effect (silently
would have made these tests exercise the REAL network path instead of the
fake). Re-pointed all four `monkeypatch.setattr` calls at
`frob.vet._hook`'s own now-local `_fetch_publish_date` binding. Verified
red before the fix (AssertionError from the real registry 404) and green
after; grepped the rest of the vet leaf-module set (_cache/_capability/
_source/_ecosystem/_lifecycle/_obfuscation/_osv/_supplychain) for the same
collision shape -- none found elsewhere in tests/.

Evidence: tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
  (new repro test: runs the real cycle detector -- frob.check._python._build_import_graph
  + frob.cycle.graph.find_cycles -- against this repo's own src/ tree and asserts no
  cycle contains a vet cluster member. FAILED_AT_PARENT confirmed at dad39134e
  (repro-only commit); PASSED after the fix commit 4352f926e.)
  Also bound to acceptance[0], acceptance[1] (must-still-pass control), acceptance[2].
  Touched-set: `uv run frob test --base main` -- 11 python outcomes recorded, all PASS
  (includes the fixed TestQuarantine cases); full `tests/test_vet.py` run separately
  as a sanity check -- 461 passed, 0 failed.

Manual verification of the must-still-pass control:
  Before this ticket (post-T-2232 land, main tip): 2 errors -- gates/lang/graph
  cluster and tickets/app/serve/verify mega-cluster (errors); vet WARNING cluster
  present; 5 note-severity 2-node clusters.
  After fix: 2 errors, 0 warnings -- vet cluster is GONE; the gates/lang/graph
  cluster, the tickets/app/serve/verify mega-cluster, and all 5 note-severity
  clusters are UNCHANGED.

Filed: none (no out-of-scope work found)

Gates: frob check --ticket T-2233 -- gate:AFFECT clean (4 sites waived with
  reasoned justifications), gate:SCOPE/gate:PRE refreshed via `frob ticket
  scope --add` + `frob ticket sweep`; no other gate family's counts changed
  by this diff (all repo-wide, pre-existing per the check's own scope-note).

### Changed
```
 src/frob/vet/_closedworld.py            | 32 +++++++++++++++----
 src/frob/vet/_hook.py                   | 25 +++++++++++----
 src/frob/vet/_scan.py                   | 55 +++++++++++++++++++--------------
 src/frob/vet/_scan_violations.py        |  7 +++--
 tests/test_vet.py                       | 16 +++++-----
 tests/unit/test_vet_cycle_regression.py | 48 ++++++++++++++++++++++++++++
 tickets/T-2233/ticket.md                | 24 +++++++++++---
 7 files changed, 155 insertions(+), 52 deletions(-)
```

### Evidence
- `tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2232-t2233/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t2232-t2233/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
