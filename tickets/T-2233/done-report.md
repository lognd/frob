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
