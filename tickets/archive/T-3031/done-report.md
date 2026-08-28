## Done report

Root cause investigation confirmed BOTH REF001 and MILE003 as described
in the ticket. Disposition per finding:

- REF001 on node_modules/package.json/tsconfig.json: REAL PRODUCT
  DEFECT. `_DEFAULT_ROOT_MANIFEST_EXEMPT` (T-3019) covered pyproject.toml/
  frob.toml but not their JS/TS-world analogs package.json/tsconfig.json;
  and ref_gate never consulted frob.excludes.BUILTIN_SKIP_DIRS (only
  [graph].exclude globs), so a committed/symlinked node_modules at a
  project root fired REF001 on that tracked entry even though every
  other stage in this repo already prunes that directory name. Fixed in
  src/frob/gates/_refs.py: package.json/tsconfig.json added to
  _DEFAULT_ROOT_MANIFEST_EXEMPT; new _is_under_vendored_tree helper skips
  any path under a BUILTIN_SKIP_DIRS name.

- REF001 on tickets.md/src.ts: TEST FIXTURE gap, not a product bug --
  each is an inherent single-file-in-an-isolated-fixture orphan, the
  exact same shape _make_project's own frob.toml already documents and
  accommodates (REF001 = "warn") for its Python __init__.py (T-3019).
  Applied the identical accommodation to the TS fixture's own frob.toml.

- MILE003 on T-0329: TEST FIXTURE staleness, not a product bug -- MILE003
  requires every OPEN ticket to resolve a milestone, and correctly does
  so here: this fixture's synthetic T-0329 was written before MILE003
  existed and never got a milestone field. Not "the real tickets.md"
  leaking in -- it is the fixture's OWN isolated tickets.md, just missing
  a field a real project's ticket would also need. Added
  milestone: '0.1.0' to the fixture ticket.

Evidence:
- tests/system/test_cli_check.py::TestCheckTypescript::{test_clean_ts_passes_tsc,test_type_error_fails_tsc}
- tests/test_refs_gate.py::TestJsTsRootManifestExempt::{test_root_package_json_and_tsconfig_are_exempt_with_no_declaration,test_nested_package_json_still_subject_to_ref001}
  (BUG002: the first confirmed FAILING at the parent commit)
- tests/test_refs_gate.py::TestVendoredTreeExempt::{test_node_modules_root_entry_is_exempt,test_a_real_orphan_outside_any_vendored_tree_still_fires}
  (BUG002: the first confirmed FAILING at the parent commit; the pair is
  the must-fire/must-stay-quiet fixture)
- full tests/test_refs_gate.py (34) and tests/unit/gates/test_refs.py (7)
  suites, clean
- `frob test --base main`: 3 PRE-EXISTING failures selected
  (TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool,
  TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root,
  TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses)
  -- confirmed independently reproducing at the PARENT commit (reverted
  this ticket's own diff, reran the 3 in isolation, identical failures)
  before this ticket's diff ever touched anything; two of the three
  (T-3028, T-3030) were already filed by T-3019's own land, the third
  filed here as T-draft-36006d55 (gets a real id at land/renumber).

Filed: T-draft-36006d55 ("TestGitlessTargetGateSeverity::
test_render_lint_gate_warns_not_errors_on_gitless_root fails on main")
-- gets a real ticket id at land/renumber time.

Gates: `frob check --ticket T-3031 --only affect_drift --only fmt --only
scope --only prework --only coverage` clean for this ticket's touched
files -- remaining gate:COV/DRIFT/DSL/WAIVE errors are pre-existing,
repo-wide, and untouched by this ticket's diff, per gate:scope-note.

### Changed
```
 src/frob/gates/_refs.py            | 56 ++++++++++++++++++++++-
 tests/system/test_cli_check.py     | 14 ++++++
 tests/test_refs_gate.py            | 92 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3031/ticket.md           | 43 +++++++++++++++++-
 tickets/T-draft-36006d55/ticket.md | 40 +++++++++++++++++
 5 files changed, 242 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 83 error(s), 674 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3065/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/ticket_runner/_new.py, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@src/frob/app/_config_external.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
