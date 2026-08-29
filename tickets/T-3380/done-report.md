## Done report

Repo-wide `ruff format .` sweep. `ruff format --check .` measured 81
files needing reformatting when Series ED first found it; re-measured
against current main immediately before this land (several lands had
landed since) and it was down to 78 -- ran `ruff format .` on those 78,
committed as a single standalone commit, nothing else batched with it.

Confirmed `gate:FMT` (FMT001) is why this went unowned: it only scans
frob: directive-comment lines touched by the CURRENT DIFF, never the
whole tree, per its own scope-note in `frob check` output -- so a
repo-wide ruff-format drift like this is invisible to the normal gate
pipeline.

Confirmed disjoint from the repo's own `frob fmt --check` (frob:
directive-line formatter): that tool flags 5 Rust files
(frob-core/src/*.rs, strata-core/src/**/*.rs), zero overlap with ruff
format's Python file set. The two tools cannot fight each other on
this sweep -- running one does not dirty what the other wants.

Mechanical only: `ruff format .` output, no logic edited by hand.
`ruff format --check .` now reports "1312 files already formatted, 0
would be reformatted" repo-wide.

### Changed
```
 .claude/hooks/root-write-guard.py                  |   4 +-
 src/frob/_cli_parsers/_ops.py                      |   2 +-
 src/frob/app/stats_runner.py                       |   2 +-
 src/frob/app/status_runner.py                      |  10 +-
 src/frob/app/sys_runner.py                         |   3 +-
 src/frob/app/ticket_runner/_query.py               |   4 +-
 src/frob/findings.py                               |   6 ++
 src/frob/gates/_lexical_selfcheck.py               |   2 -
 src/frob/gates/_models.py                          |   9 +-
 src/frob/gates/_mutation_evidence.py               |   2 -
 src/frob/gates/_port_selfcheck.py                  |   1 -
 src/frob/gates/_tdd_order.py                       |   4 +-
 src/frob/gates/_version_coupling.py                |   4 +-
 src/frob/gates/_walk_lint.py                       |  10 +-
 src/frob/ghio.py                                   |   8 +-
 src/frob/graph/dsl.py                              |   4 +-
 src/frob/graph/reach.py                            |   6 +-
 src/frob/process/_lock.py                          |   1 +
 src/frob/serve/_socketd.py                         |   5 +-
 src/frob/stats/_agentic.py                         |   6 +-
 src/frob/strata/_selfconform.py                    |   2 +-
 src/frob/strata/_selfconform_core_rules.py         |   1 -
 src/frob/strata/_selfconform_kinds.py              |   3 -
 src/frob/strata/_selfconform_models.py             |   2 -
 src/frob/strata/_selfconform_surface_rules.py      |   1 -
 src/frob/tickets/_archive.py                       |   7 +-
 src/frob/tickets/_done_report.py                   |   4 +-
 src/frob/tickets/_land_compose.py                  |   5 +-
 src/frob/tickets/_land_release.py                  |  12 +--
 src/frob/tickets/_models.py                        |   1 +
 src/frob/tickets/_reporting.py                     |   1 +
 src/frob/tickets/_store.py                         |   1 +
 .../_dangerous_ops_bash_csharp.py                  |  18 ++--
 src/frob/vet/_capability_registry/_matrix.py       |   3 +-
 src/frob/vet/_supplychain.py                       |   1 -
 tests/gates/test_comment_placement.py              |  50 +++------
 tests/integration/test_interfaces.py               |   2 +-
 tests/system/test_cli_perf.py                      |   4 +-
 tests/test_check_runner.py                         |  14 +--
 tests/test_ci_report.py                            |  44 ++++++--
 tests/test_ci_validity.py                          |  20 +++-
 tests/test_gates.py                                |  19 +---
 tests/test_gates_vmodel.py                         |  25 +++--
 tests/test_ghio.py                                 |  29 +++---
 tests/test_graph_reach.py                          |  16 +--
 tests/test_measure_evidence_reach.py               |  31 +++---
 tests/test_mutate.py                               |   4 +-
 tests/test_refs_gate.py                            |  16 ++-
 tests/test_status.py                               |   4 +-
 tests/test_ticket_land_lint_diff_attribution.py    |   6 +-
 tests/test_ticket_land_ty_diff_attribution.py      |   6 +-
 tests/test_tickets_cmd_evidence.py                 |   8 +-
 tests/test_tickets_no_scope.py                     |   3 +-
 tests/test_vet.py                                  |   4 +-
 tests/test_vet_capability.py                       |   4 +-
 tests/test_walk_lint_gate.py                       |   6 +-
 tests/unit/gates/test_lock_producer.py             |   8 +-
 tests/unit/gates/test_refs.py                      |   6 +-
 tests/unit/gates/test_version_coupling.py          |   3 +-
 tests/unit/graph/test_dsl_markdown_waive.py        |   5 +-
 tests/unit/strata/test_bootstrap.py                |   4 +-
 tests/unit/strata/test_shrink.py                   |  21 ++--
 tests/unit/strata/test_vmodel_authoring.py         |   8 +-
 tests/unit/strata/test_vmodel_check.py             |  28 ++++-
 tests/unit/test_app_runners_batch7.py              |   8 +-
 tests/unit/test_close_blocked_by_guard.py          |   4 +-
 tests/unit/test_doctor.py                          |   4 +-
 tests/unit/test_land_finish_idempotent.py          |   4 +-
 tests/unit/test_land_release_out_of_tree.py        |  18 +---
 tests/unit/test_land_stage_flip.py                 |  17 +--
 tests/unit/test_lang_strata_entity_arch.py         |   4 +-
 tests/unit/test_rapid_debt.py                      |   4 +-
 .../test_reporting_t3285_fenced_subheadings.py     |   4 +-
 tests/unit/test_ticket_restore.py                  |  12 +--
 tests/unit/test_wire001_atexit_register.py         |   4 +-
 .../unit/test_wire001_property_attribute_access.py |   2 +-
 tests/unit/verify/test_quarantine.py               |  12 +--
 tests/unit/verify/test_verify_runner.py            |   4 +-
 tickets/T-3380/done-report.md                      | 115 +++++++++++++++++++++
 tickets/T-3380/ticket.md                           |  16 ++-
 80 files changed, 423 insertions(+), 362 deletions(-)
```

### Evidence
- `tests/test_ghio.py::TestPreflight::test_not_installed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 47 error(s), 6947 warning(s), 880 waived
- error-findings: AFFECT001@.claude/hooks/root-write-guard.py, AFFECT001@src/frob/app/status_runner.py, AFFECT001@src/frob/gates/_version_coupling.py, AFFECT001@src/frob/ghio.py, AFFECT001@src/frob/tickets/_land_compose.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC004@docs/commands/check.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/modules/tickets.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py
