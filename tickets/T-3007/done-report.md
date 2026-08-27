## Done report

Changed:
- strata-core/src/graph/vmodel.rs (new) -- KIND_ARTIFACT/KIND_TEST/KIND_DECISION,
  the ten V-model level constants, v_pairing(), v_model_schema() (the
  GraphSchema instance: satisfies/verifies/refines/allocates/decides/
  supersedes/blocked_by edge kinds, verifies carrying the LevelRelation::Paired
  map), ClosureViolation, and the four rule functions
  (check_no_orphan_requirements, check_no_unjustified_design,
  check_no_untested_artifact, check_no_orphan_test) plus check_closure.
- strata-core/src/graph/mod.rs -- added `pub mod vmodel;`.
- strata-core/src/lib.rs -- added `vmodel_check` PyO3 function (data-in/
  data-out: node/edge tuples in, construction-error strings + closure
  violations out) and registered it in the `strata_core` pymodule; added
  two Rust unit tests for it.
- docs/strata/graph.md -- updated the "Deferred" section: the instance
  schema and PyO3 surface this note pointed at are no longer deferred,
  point to docs/strata/vmodel.md.
- docs/strata/vmodel.md (new) -- module doc: node/edge kinds, the V pairing
  table, the four closure rules, and the vmodel_check PyO3 contract.
- docs/strata/kernel.md -- one-line addendum to the strata_core pymodule
  bullet (AFFECT001: strata_core's affects-closure doc), pointing to
  docs/strata/vmodel.md.

Schema supplied: node kinds `artifact`/`test`/`decision`; ten levels (five
V-model pairs: requirements/customer-test,
requirement-specification/customer-test-plan,
system-specification/system-integration-test-plan,
system-design/subsystem-integration-test-plan,
component-design/component-unit-test); edge kinds satisfies (artifact->
artifact, Any), verifies (test->artifact, Paired per the table above),
refines/allocates (artifact->artifact, Any), decides (decision->artifact,
Any), supersedes and blocked_by (unconstrained).

Four closure rules, each with a must-fire and a must-stay-quiet fixture
(strata-core/src/graph/vmodel.rs::tests):
1. check_no_orphan_requirements -- every non-innermost-level artifact needs
   >=1 incoming `satisfies` edge (rule1_must_fire_on_orphan_requirement /
   rule1_must_stay_quiet_when_satisfied). The innermost level
   (component-design) is exempt: nothing more detailed exists to satisfy it.
2. check_no_unjustified_design -- every non-outermost-level artifact needs
   >=1 outgoing satisfies/refines/allocates edge
   (rule2_must_fire_on_unjustified_design / rule2_must_stay_quiet_when_traced).
   The outermost level (requirements) is exempt: nothing above it to trace to.
3. check_no_untested_artifact -- every artifact needs >=1 incoming `verifies`
   edge (rule3_must_fire_on_untested_requirement /
   rule3_must_stay_quiet_when_verified_at_paired_level), plus
   rule3_wrong_level_test_is_refused_at_construction_not_silently_accepted
   proving a wrong-paired-level verifies edge is refused by the KERNEL at
   construction, before this rule ever sees the graph.
4. check_no_orphan_test -- every test needs >=1 outgoing `verifies` edge
   (rule4_must_fire_on_orphan_test / rule4_must_stay_quiet_when_verifying_something).

check_closure_is_empty_on_a_fully_closed_two_level_graph and
check_closure_reports_all_four_rules_on_a_maximally_broken_graph exercise
all four together.

PyO3 surface: only `vmodel_check(nodes, edges) -> (errors, violations)`.
strata-core::graph as a whole stays Rust-internal; this is the one
operation a Python caller needs to build a V-model graph from flattened
data and get back both construction refusals and closure violations in one
call. A broader export (raw Graph/GraphSchema bindings) is deliberately not
built -- T-3008/T-3009/T-3010 are Rust-API consumers of this crate, add
more only when a concrete caller needs it.

Scope note: docs/strata/kernel.md was added to scope mid-ticket
(`frob ticket scope T-3007 --add`) after AFFECT001 flagged that touching
the `strata_core` pymodule fn (adding vmodel_check's registration) requires
touching its declared affects-closure doc.

Evidence: cargo is the real test surface for this Rust-only module.
`cargo test --lib graph::vmodel::` = 11 passed; `cargo test --lib
vmodel_check` = 2 passed; `cargo test --lib` (whole crate) = 168 passed, 0
failed (was 166 before this ticket, +2 new lib.rs tests; graph module tests
went from 18 to 29, +11 new vmodel.rs tests). No PyO3 surface of its own
beyond vmodel_check, already covered by the two cargo tests above and
manually verified end-to-end via `python -c "import strata_core;
strata_core.vmodel_check(...)"`. Per T-3005's precedent (this ticket's
direct predecessor, same "Rust-only, no new pytest surface" situation),
evidence is bound to the same two existing strata-core-crate-exercising
pytest node ids that prove the crate (this new module included) still
compiles and the pyo3 extension still loads cleanly:
- tests/unit/strata/test_parse.py::TestParseModule::test_parses_bare_module
- tests/unit/strata/test_parse.py::TestParseModule::test_round_trip_small_design
Both re-run green post-change (2 passed, 0 failed).

Filed: none.

Gates: `frob check --only affect_drift --json` clean for gate:AFFECT (the
one AFFECT001 finding this ticket triggered was fixed by the kernel.md
addendum above, then re-verified clean). `frob check --budget 480 --ticket
T-3007` shows failures across many gate families, but per that command's
own scope-note, --ticket only scopes gate:SCOPE/gate:PREWORK and the
diff-driven checks inside gate:COV/gate:FMT/gate:AFFECT -- every other
family's count is REPO-WIDE pre-existing baseline noise (verified none of
it names strata-core/src/graph/vmodel.rs, the new docs files, or the
touched lib.rs/mod.rs lines). `frob fmt --check` lists 6 files that would
reformat, none of them touched by this ticket. `cargo test -p strata-core
--lib` clean (168 passed, 0 failed).

Follow-up within this ticket (same commit series): the full `--ticket
T-3007` gate run surfaced real COV001 (missing frob:doc), DOC002 (target
anchor didn't exist), TEST001 (v_pairing/v_model_schema had no direct
unit test), and REF002 (single inbound reference) findings against the
NEW files -- these are diff-driven, not repo-wide noise, so they were
fixed rather than left: every new public symbol in
strata-core/src/graph/vmodel.rs and lib.rs::vmodel_check now carries a
frob:doc edge into a real anchored section of docs/strata/vmodel.md
(#node-kinds, #levels-the-v-pairing-t-3004-section-1, #edge-kinds,
#schema-assembly, #the-four-closure-rules-t-3004-section-2,
#pyo3-surface-vmodel_check); v_pairing_has_five_pairs_in_t3004_order and
v_model_schema_declares_every_kind_level_and_edge_kind were added as
direct unit tests; REF002's single-inbound-reference note on
vmodel.rs/vmodel.md is waived with a reason (first consumer of the
kernel, second reference expected once T-3008/T-3009/T-3010 land). Full
`cargo test -p strata-core --lib` after these fixes: 170 passed, 0
failed. Re-ran `frob check --only coverage --only test --only refs
--only docanchor --json` afterward and confirmed zero remaining
errors/unresolved findings against vmodel.rs, lib.rs, or vmodel.md (only
a waived REF002 note remains); all other errors in that run are in
unrelated pre-existing files (e.g. src/frob/tickets/_leases.py,
tests/unit/test_logging_module.py).

### Changed
```
 docs/strata/graph.md            |  11 +-
 docs/strata/kernel.md           |   6 +-
 docs/strata/vmodel.md           | 138 ++++++++++
 strata-core/src/graph/mod.rs    |   7 +
 strata-core/src/graph/vmodel.rs | 550 ++++++++++++++++++++++++++++++++++++++++
 strata-core/src/lib.rs          | 107 ++++++++
 tickets/T-3007/done-report.md   | 120 +++++++++
 tickets/T-3007/ticket.md        |  64 ++++-
 8 files changed, 996 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/strata/test_parse.py::TestParseModule::test_parses_bare_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_parse.py::TestParseModule::test_round_trip_small_design` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 56 error(s), 720 warning(s), 855 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3007/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3007, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/gates/_narrative_blocks.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md
