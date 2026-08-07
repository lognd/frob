## Done report

Wired T-0595's optional binding/root join all the way through every production discharge entrypoint in scope:

- `_audit.py::evaluate_exhaustiveness` gained a `root: Path | None = None`
  param; when given, it calls `bind_code(model, root)` once and threads the
  resulting `CodeBinding` (plus `root`) through `_collect_all_family_gaps`
  -> `_threat_and_quality_gaps` -> `_evaluate_family` -> `check_discharge_
  completeness`, for every security AND quality view. `bind_code`'s
  `Err(StrataError.AmbiguousCodeBinding)` propagates fail-closed.
- `_sysdoc.py::render_audit_matrix` gained the same `root:` param, computes
  its own binding, threads it through `_check_matrix_completeness` into
  `check_discharge_completeness` -- the human-facing matrix's FAILING rows
  now reflect the G1 stronger half too.
- `_plan.py::plan_obligations` gained `root:`, computes binding, passes it
  into `_frontier_threats` -> `evaluate_threats(..., binding=, root=)` so a
  code-unbound THREAT003 gets planned as a real ticket.
- `vet/_containment.py::build_containment_report` already had `binding`/
  `root` in hand (used by `find_importing_nodes`) but its own
  `_undischarged_pairs` call to `check_discharge_completeness` silently
  omitted both -- now threads them through directly (this was the
  cheapest, most direct instance of the catalogued-is-not-enforced gap).

Real finding surfaced: wiring `_containment.py` made
`tests/test_vet_containment.py::TestBuildContainmentReport::
test_contained_finding_when_obligation_discharged`'s fixture fail --
its `api.py` fixture never actually CALLED `parameterization`, only
resolved the claim (T-0498's weaker half). Fixed the fixture honestly by
adding a real `parameterization(...)` call site, per the dispatch's own
guidance ("fix the model honestly ... with scope-add + disclosure").
Scope-added via `frob ticket scope --add` with reason recorded in the
ticket's `scope_changes` audit trail (not a silent edit).

Coordination note: `frob.app.sys_runner.py` (`_evaluate_audit`/`_run_doc`/
`_run_plan`) is where `root` is ALREADY resolved for every real CLI
invocation (`_resolve_design_root`) but that file is explicitly out of
this ticket's scope (T-0724 concurrently wiring
`check_resource_contention` into it). Per the dispatch's own coordination
instruction, I did NOT edit it -- reporting instead: `evaluate_exhaustiveness`,
`render_audit_matrix`, and `plan_obligations` all now accept `root=`, but
`sys_runner.py`'s three call sites (`_evaluate_audit`, `_run_doc`,
`_run_plan`) still call them WITHOUT `root=`, so `frob sys audit`/`sys doc`/
`sys plan` invoked from the real CLI today still do not pass a code tree --
the entrypoints are wired and ready, but the last one-line-per-callsite
connection from `sys_runner.py` is the remaining gap. This needs either a
follow-up ticket once T-0724 lands, or a small addition folded into
T-0724's own landing since it already touches that exact file.

New unit test class `tests/unit/strata/test_audit.py::TestCodeBoundWiring`
(3 tests) proves the wiring at the `evaluate_exhaustiveness` level: an
unbound `output_encoding` predicate on a real `tmp_path` fixture repo
surfaces as a named THREAT003 gap through the real gate function (not a
hand-constructed `check_discharge_completeness` call), a real call site
still proves clean, and omitting `root` preserves the pre-T-0630 model-only
posture.

Gates: `frob check --ticket T-0630` clean (0 errors, 405 warnings, 200
waived -- all pre-existing repo-wide, none newly introduced by this
ticket's diff). Version bumped 0.89.0 -> 0.90.0 (REL001, public API
change: 4 functions gained new optional params) with a CHANGELOG.md entry;
scope extended (with recorded reasons) to cover
`tests/test_vet_containment.py`, `pyproject.toml`, `uv.lock`,
`CHANGELOG.md` as direct, narrow consequences of this ticket's own change.

Pre-existing, unrelated failures observed and left untouched (not part of
this ticket's scope): `tests/unit/strata/test_export_golden.py` (k8s/
seccomp/iam golden-file drift, unrelated to threat/discharge wiring, no
import of anything this ticket touches).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_root_wires_real_code_binding_and_surfaces_threat003` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_root_with_real_call_site_still_proves_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_no_root_preserves_pre_t0630_model_only_posture` (pytest node id, verified passing when recorded)
- `tests/test_vet_containment.py::TestBuildContainmentReport::test_contained_finding_when_obligation_discharged` (pytest node id, verified passing when recorded)
