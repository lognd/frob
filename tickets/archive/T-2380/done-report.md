## Done report

: T-2380 SYS003 gate calibration

Coordinator accepted the (b) over-firing verdict from the T-0969
measurement (4834 findings) and directed a fix: declare rather than
special-case, verify before reclassifying, re-measure honestly,
positive-control mandatory, then decide single-dispatch-vs-children on
the TRUE remainder.

### 1. Chosen fix shape: declaration in the model, not a gate special-case

Confirmed via `src/frob/gates/_sys.py::_sys003_one_model` +
`src/frob/strata/_code_binding.py::check_import_conformance` that the
gate's allow-set (`_declared_pairs`) is an EXACT set of (owner, dst_owner)
tuples derived from `Flow` declarations -- no wildcard mechanism exists
at the strata language level. So the only way to "prefer a declaration
over a special case" was the one every other cross-component dependency
in this repo already uses: one explicit `flow f_testsuite_X : testsuite
-> X { ... }` per component the test suite genuinely imports. Declared
18 (tickets_ledger, gates, graphlang, cli, core, vet, stratamod, checker,
verify, refactor, serve, mutate, registry_model, deploy, natives, fleet,
security, telemetry -- the last 3 found only after the first pass, via
iterative re-measurement). This is NOT a `testsuite -> *` wildcard: it
does not touch production -> testsuite (still fires, no Flow declared
that direction) and does not cover any component not on this list (still
fires for a future 19th component with no Flow).

### 2. Verified shared-utility ownership BEFORE reclassifying

Read design/frob.strata directly rather than trusting the T-0969 guess:
`frob.excludes`/`frob.yamlio`/`frob.tomlio` were declared under node
`cli` (T-0500's "loose top-level file needs SOME owner" rationale, an
explicit historical decision, not an oversight). Confirmed via the
production-only finding breakdown that 8+ unrelated components (gates,
vet, tickets_ledger, stratamod, refactor, checker, core, registry_model)
import these three and they import nothing back -- the shape of a
misplaced cross-cutting leaf utility, not a genuine dependency on the CLI
entrypoint layer. Moved all three to node `core` (this repo's existing
general-infra node, which already owns the same-shaped `gitio.py`),
carrying their `may fs.write via` capability declarations with them.
Updated the stale T-0500 doc comment in place rather than leaving it
describing code that moved. `doctor.py` (only 1 production finding, a
genuine CLI diagnostic subcommand) was deliberately NOT moved.

### 3. Declared the 3 remaining genuine missing Flows

`refactor -> core`, `registry_model -> core`, `verify -> core`
(frob.logging/frob.gitio dependencies, already correctly modeled under
`core`, just never declared from these three callers).

### 4. Count delta (measured, not budgeted-and-trusted)

`uv run frob check --only sys --json`, confirmed `gate-summary` present
and zero `BUDGET001` deferral before trusting the number, both before and
after:

- Before: 4834 (4610 testsuite-origin, 224 production, of which 86
  clustered on the 5 misplaced-utility modules)
- After: 133, ALL production, ZERO testsuite-origin
- Delta: -4701 (-97.25%)

The remaining 133 are genuine undeclared production cross-component
imports (verified by reading samples: `src/frob/app/graph_runner.py`
importing `frob.verify._selection` with no `cli -> verify` Flow, etc.) --
real work, not calibration noise. Filed as T-2404 (single-dispatch burn-
down + WARN->ERROR promotion), not split into multiple children: 133
spans ~45 distinct (from, to) pairs but is one coherent task (declare-or-
fix, case by case) sized similarly to T-0969's other single-dispatch
buckets.

### 5. Positive control (mandatory, both directions)

`tests/unit/strata/test_sys003_calibration.py`, 4 tests, using
frob.strata's own Python `KernelModel`/`Flow`/`Node` construction API
(same pattern as `tests/test_gates.py::test_sys003_import`):

- `test_must_now_be_silent__testsuite_importing_declared_tested_module`:
  a normal test importing its declared, tested module -> SYS003 silent.
- `test_must_still_fire__testsuite_importing_undeclared_component`: the
  SAME testsuite node importing a component with NO declared Flow ->
  SYS003 still fires. Proves this is a set of explicit edges, not a
  blanket exemption.
- `test_must_still_fire__production_importing_testsuite`: the reverse
  direction, no Flow declared either before or after this ticket -> still
  fires.
- `test_must_still_fire__genuine_undeclared_production_cross_import`: an
  independent production-to-production baseline, untouched by the
  testsuite Flow work at all -> still fires. Stable must-still-fire
  fixture the calibration work cannot accidentally weaken.

All 4 pass. `tests/test_gates.py::TestSysGate::test_sys003_import` (the
pre-existing synthetic-model regression) still passes unchanged.
`tests/unit/strata/test_selfconform.py::TestCoverageTotality::
test_repo_unrestricted_scan_is_clean` (repo-wide capability-declaration
totality) passes -- required adding the new test file itself to
testsuite's `may fs.write via` list (its own `_write` helper writes
fixture files) after first misplacing it in the fs.READ list by mistake
on the first attempt; corrected and reverified.

### Acceptance

- [0] (amended): true production-only count measured (133, from 4834),
  bound to all 4 test_sys003_calibration.py evidence ids; children filed
  (T-2404) per the corrected count.
- [1]: not yet met -- SYS003 promotion to ERROR is explicitly T-2404's
  job, gated on T-2404 landing clean, not this ticket's.

### Filed

T-2404: Burn down the 133 genuine SYS003 findings post-calibration, then
promote to error (parent T-0969).

### Cuts

None. `frob check --land-parity` and `--ticket T-2380` show no NEW errors
attributable to this change (F401 in vet/_capability.py and DRIFT002 for
docs/modules/vet.md are pre-existing drift from an unrelated concurrent
land during this session, not touched by this ticket's scope; COV002
design/frob.strata appeared once under `--land-parity`'s own internal
budgeted sub-check and did not reproduce in two separate direct
re-measurements -- treated as cache/contention noise per playbook section
6, not a real finding, and re-checked immediately before landing).

### Changed
```
 design/frob.strata                           | 100 +++++++++++++++---
 tests/unit/strata/test_sys003_calibration.py | 145 +++++++++++++++++++++++++++
 tickets/T-2380/ticket.md                     |  29 +++++-
 3 files changed, 260 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_now_be_silent__testsuite_importing_declared_tested_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__testsuite_importing_undeclared_component` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__production_importing_testsuite` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2380/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2380/src/frob/vet/_capability.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2380, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [0] replace: 'given a fresh SYS003 measurement, when findings are grouped by (from_component, to_component), then one or more disjoint-scope children are filed covering the full 4834' -> "GIVEN the corrected architecture model (testsuite->component Flows declared explicitly per T-2380's investigation, frob.excludes/yaml_io/tomlio reclassified from cli to core, refactor/registry_model/verify->core Flows added) THEN a fresh unscoped frob check reports the TRUE production-only SYS003 count, and that count is either burned down in one dispatch or split into disjoint children" (reason: criterion 0 assumed 4834 genuine findings needing distribution across children; the coordinator-accepted verdict is that ~95%+ of that count is gate over-firing (testsuite importing tested production code, plus 3 misplaced leaf utilities), so 'file children covering the full 4834' is now the wrong instruction -- the model must be corrected FIRST, then the true remainder measured and only then decomposed; logan, 2026-08-18)
