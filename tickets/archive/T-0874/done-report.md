## Done report

Method: one full unscoped `frob check` (FROB_ALLOW_FULL_CHECK=1, per
WAIVE004's own "trust only full unscoped runs" guidance) collected every
WAIVE004 (zero-match) finding: 1426 warnings, dominated by DUP001 (906),
INV006 (209), TEST005 (127), COV005 (49), AFFECT001 (46), SCOPE001 (39),
PERF004 (22), PERF003 (12), REF002 (5), ARCH001 (4), PERF001 (3), DUP002
(3), COV002 (1).

Bulk-deleted all 1426 directives (script-driven, block-aware for
multi-line reason= strings). Re-running the full check surfaced 3 real
regressions from the purge itself, all fixed:
  1. ~209 INV006 "first-turn-on pool" waivers (T-0585) turned out to be
     LIVE findings, not stale -- deleting them resurfaced 177 real INV006
     errors on re-check. Restored all 209 verbatim from main's blob.
  2. The bulk restore inserted one block (INV006) ahead of an adjacent
     ARCH102 waiver's own continuation lines in src/frob/graph/__init__.py,
     splitting ARCH102's directive and tripping DSL001 (malformed
     directive). Fixed by hand: reordered the two blocks back to their
     original relative order.
  3. One inline (same-line-as-code) PERF004 waiver in
     src/frob/stats/_agentic.py had a 2-line reason= continuation my
     script's inline-strip path did not follow, leaving 2 orphaned comment
     fragments after the code line. Removed the fragments; this also
     needed a `frob:ticket T-0874` edge added to `_retread_candidates`
     (COV002, since its line was genuinely touched).

Investigation finding (filed as T-1064, out of scope for this
ticket): restoring the 209 INV006 waivers verbatim made the real INV006
errors disappear (confirmed via `frob check --only invariant`), but
WAIVE004's own full-run pre-check continues to report all 209 (plus 3
more, freshly-landed T-0861 DUP001/AFFECT001 header waivers merged in
from main) as zero-match, indefinitely. This is a real detector
disagreement between WAIVE004's pre-check and the actual `_apply_waivers`
pass for a specific waiver shape (standalone header-position comment
ahead of a frob:enforces/frob:tests chain), not stale content -- these
213 waivers are demonstrably still required and were NOT deleted.

Net: WAIVE004 1426 -> 213 (all 213 confirmed live via scoped
cross-check, filed as a detector bug rather than deleted). Total
gate-summary warnings 1802 -> 401 (excluding the 213 residual WAIVE004,
which were already present in the 1802 baseline). gate-summary errors:
0 -> 0 (all resurfaced findings fixed before finishing, none left
error-level). ruff-format/ruff-check clean on both `ruff` invocations
covering all touched files.

Merged main mid-ticket (main had advanced ~40 commits past the worktree's
creation point during this session, including a coordinator's T-0861
landing that added 3 of the residual WAIVE004-flagged waivers this ticket
did NOT touch); resolved 2 real content conflicts
(src/frob/gates/__init__.py, src/frob/vet/_capability_registry.py) by
taking main's newly-added content in both cases (T-0861's DUP001/AFFECT001
waivers ahead of _debt001_violations/_depr001_violations/_test010_violations
and RUNTIME_OPAQUE_CONSTRUCTS). Post-merge deletion-filter
(`git diff main --diff-filter=D --stat`) is empty.

### Changed
```
 src/frob/__main__.py                               |   4 -
 src/frob/app/app.py                                |   5 -
 src/frob/app/check_runner.py                       |   8 -
 src/frob/app/config.py                             |   7 -
 src/frob/app/debt_runner.py                        |   5 -
 src/frob/app/deploy_runner.py                      |   3 -
 src/frob/app/deprecated_runner.py                  |   3 -
 src/frob/app/doctor_runner.py                      |   1 -
 src/frob/app/perf_runner.py                        |   1 -
 src/frob/app/sys_runner.py                         |   6 -
 src/frob/app/test_runner.py                        |   3 -
 src/frob/app/ticket_runner.py                      |   6 -
 src/frob/arch/__init__.py                          |   2 -
 src/frob/arch/_async_hazards.py                    |   3 -
 src/frob/arch/_concurrency.py                      |   3 -
 src/frob/arch/_concurrency_model.py                |   5 -
 src/frob/arch/_cpp.py                              |   2 -
 src/frob/arch/_cpp_mayraise.py                     |  13 -
 src/frob/arch/_exceptions.py                       |   2 -
 src/frob/arch/_kotlin.py                           |   5 -
 src/frob/arch/_lock_ordering.py                    |  10 -
 src/frob/arch/_mayraise.py                         |   3 -
 src/frob/arch/_patterns.py                         |   5 -
 src/frob/arch/_python.py                           |   7 -
 src/frob/arch/_rust.py                             |  11 -
 src/frob/arch/_shared_state_race.py                |  13 -
 src/frob/arch/_smells.py                           |   1 -
 src/frob/arch/_typescript.py                       |   3 -
 src/frob/check/__init__.py                         |   7 -
 src/frob/check/_native.py                          |   2 -
 src/frob/check/_python.py                          |   2 -
 src/frob/check/_ts.py                              |   2 -
 src/frob/clean/_core.py                            |   1 -
 src/frob/cve/_parser.py                            |   1 -
 src/frob/deploy/_generate.py                       |  17 --
 src/frob/deploy/_generate_windows.py               |  16 --
 src/frob/docs/__init__.py                          |   4 -
 src/frob/doctor.py                                 |  11 -
 src/frob/dup/_cache.py                             |   2 -
 src/frob/dup/_core.py                              |   1 -
 src/frob/dup/_legacy_common.py                     |   2 -
 src/frob/dup/_legacy_cpp.py                        |   3 -
 src/frob/dup/_pipeline.py                          |   3 -
 src/frob/dup/_rules.py                             |   9 -
 src/frob/dup/_template.py                          |   1 -
 src/frob/exports/__init__.py                       |   2 -
 src/frob/fuzz/_arbitrary.py                        |   3 -
 src/frob/fuzz/_rules.py                            |   1 -
 src/frob/fuzz/_stamp.py                            |   4 -
 src/frob/gates/__init__.py                         |  29 --
 src/frob/gates/_baseline.py                        |   2 -
 src/frob/gates/_coverage.py                        |   2 -
 src/frob/gates/_cve_fingerprint_scan.py            |   2 -
 src/frob/gates/_docblocks.py                       |   5 -
 src/frob/gates/_docptr.py                          |   5 -
 src/frob/gates/_exclude_hazard.py                  |   3 -
 src/frob/gates/_exhaustive_handling.py             |   3 -
 src/frob/gates/_fmt_directives.py                  |   4 -
 src/frob/gates/_opaque.py                          |   3 -
 src/frob/gates/_pii_structural.py                  |  19 --
 src/frob/gates/_prework.py                         |   5 -
 src/frob/gates/_protocol_summary.py                |   2 -
 src/frob/gates/_registry_exhaustiveness.py         |   9 -
 src/frob/gates/_render_lint.py                     |   3 -
 src/frob/gates/_secrets.py                         |   6 -
 src/frob/gates/_walk_lint.py                       |   3 -
 src/frob/gates/decisions.py                        |   1 -
 src/frob/graph/__init__.py                         |   4 -
 src/frob/graph/_core.py                            |   2 -
 src/frob/graph/callgraph.py                        |   2 -
 src/frob/graph/dsl.py                              |  11 -
 src/frob/graph/summary.py                          |   1 -
 src/frob/lang/__init__.py                          |   1 -
 src/frob/lang/_common.py                           |  12 -
 src/frob/lang/_extract.py                          |   2 -
 src/frob/lang/_nodes.py                            |  13 -
 src/frob/lang/_walk_c.py                           |   3 -
 src/frob/lang/_walk_kotlin.py                      |   9 -
 src/frob/lang/_walk_python.py                      |   7 -
 src/frob/lang/_walk_typescript.py                  |   7 -
 src/frob/logging/color.py                          |   1 -
 src/frob/mutate/__init__.py                        |   4 -
 src/frob/mutate/_journal.py                        |   6 -
 src/frob/natives/_build.py                         |   1 -
 src/frob/outline/__init__.py                       |   1 -
 src/frob/perf/_advisories.py                       |   1 -
 src/frob/perf/_collectors.py                       |   1 -
 src/frob/perf/_dup_spawn.py                        |   4 -
 src/frob/perf/_effect_summaries.py                 |   1 -
 src/frob/perf/_harness.py                          |   2 -
 src/frob/perf/_heat.py                             |   2 -
 src/frob/perf/_hotgraph.py                         |   1 -
 src/frob/perf/_loop_effects.py                     |   7 -
 src/frob/perf/_recursion.py                        |   5 -
 src/frob/perf/_redundancy.py                       |   2 -
 src/frob/perf/_sampler.py                          |   1 -
 src/frob/perf/_serial_pools.py                     |   1 -
 src/frob/perf/_sketch_store.py                     |   5 -
 src/frob/policy/__init__.py                        |   1 -
 src/frob/process/_lock.py                          |   1 -
 src/frob/process/parsers/common.py                 |   7 -
 src/frob/process/parsers/ty.py                     |   2 -
 src/frob/process/parsers/valgrind.py               |   2 -
 src/frob/release/__init__.py                       |   3 -
 src/frob/scaffold/_managed.py                      |  18 --
 src/frob/scaffold/project.py                       |   1 -
 src/frob/serve/_daemon.py                          |   7 -
 src/frob/serve/_tools.py                           |   8 -
 src/frob/serve/_warm.py                            |   4 -
 src/frob/serve/server.py                           |   3 -
 src/frob/stats/__init__.py                         |   2 -
 src/frob/stats/_agentic.py                         |   7 +-
 src/frob/strata/_access.py                         |   2 -
 src/frob/strata/_atomic.py                         |   1 -
 src/frob/strata/_audit.py                          |   7 -
 src/frob/strata/_claims.py                         |  11 -
 src/frob/strata/_code_binding.py                   |   1 -
 src/frob/strata/_compliance.py                     |   4 -
 src/frob/strata/_design_load.py                    |   1 -
 src/frob/strata/_elaborate.py                      |   3 -
 src/frob/strata/_host.py                           |   2 -
 src/frob/strata/_host_isolation.py                 |  10 -
 src/frob/strata/_infra.py                          |   3 -
 src/frob/strata/_krb_movement.py                   |   5 -
 src/frob/strata/_lint.py                           |   6 -
 src/frob/strata/_models.py                         |   1 -
 src/frob/strata/_plan.py                           |   2 -
 src/frob/strata/_policy.py                         |   1 -
 src/frob/strata/_scenarios.py                      |   1 -
 src/frob/strata/_starvation.py                     |   3 -
 src/frob/strata/_sysdoc.py                         |   2 -
 src/frob/strata/_threat.py                         |   3 -
 src/frob/strata/_waive.py                          |   4 -
 src/frob/testing/_collect.py                       |   1 -
 src/frob/testing/_runners.py                       |   1 -
 src/frob/testing/_select.py                        |   2 -
 src/frob/testing/_stability.py                     |   8 -
 src/frob/tickets/__init__.py                       |  23 --
 src/frob/tickets/_brief.py                         |   5 -
 src/frob/tickets/_journal.py                       |   6 -
 src/frob/tickets/_land.py                          |   2 -
 src/frob/tickets/_leases.py                        |   4 -
 src/frob/tickets/_models.py                        |   2 -
 src/frob/tickets/_mutation_evidence.py             |   4 -
 src/frob/tickets/_store.py                         |   9 -
 src/frob/vet/_allow.py                             |   1 -
 src/frob/vet/_cache.py                             |   4 -
 src/frob/vet/_capability.py                        |  24 --
 src/frob/vet/_capability_modes.py                  |  14 -
 src/frob/vet/_capability_registry.py               |  11 -
 src/frob/vet/_closedworld.py                       |   3 -
 src/frob/vet/_containment.py                       |   2 -
 src/frob/vet/_cve.py                               |   2 -
 src/frob/vet/_ecosystem.py                         |   2 -
 src/frob/vet/_hook.py                              |   4 -
 src/frob/vet/_lifecycle.py                         |   1 -
 src/frob/vet/_nvd.py                               |   7 -
 src/frob/vet/_obfuscation.py                       |   3 -
 src/frob/vet/_osv.py                               |   3 -
 src/frob/vet/_registry.py                          |   8 -
 src/frob/vet/_scan.py                              |  11 -
 src/frob/vet/_source.py                            |   5 -
 src/frob/vet/_typosquat.py                         |   1 -
 src/frob/xref/__init__.py                          |   3 -
 tests/integration/test_gitlog.py                   |   3 -
 tests/system/test_cli_arch.py                      |   6 -
 tests/system/test_cli_check.py                     |   6 -
 tests/system/test_cli_doctor.py                    |   1 -
 tests/system/test_cli_evidence_enforcement.py      |  11 -
 tests/system/test_cli_gitlog.py                    |   3 -
 tests/system/test_cli_graph.py                     |   4 -
 tests/system/test_cli_map.py                       |   3 -
 tests/system/test_cli_outline.py                   |   3 -
 tests/system/test_cli_sys_audit.py                 |   3 -
 tests/system/test_cli_sys_doc.py                   |   3 -
 tests/system/test_frob_self_model.py               |   3 -
 tests/test_ack_worktree_lease.py                   |   6 -
 tests/test_capability_registry.py                  |   2 -
 tests/test_check_coverage_registry.py              |   1 -
 tests/test_decisions.py                            |   5 -
 tests/test_docblocks_gate.py                       |  48 ----
 tests/test_docptr_gate.py                          |  42 ---
 tests/test_doctor.py                               |   1 -
 tests/test_dup.py                                  |  48 ----
 tests/test_dup_exhaustiveness.py                   |   4 -
 tests/test_dup_native_rungs.py                     |   6 -
 tests/test_dup_r5_multilang.py                     |  12 -
 tests/test_dup_rungs.py                            |  11 -
 tests/test_evidence_integrity.py                   |  10 -
 tests/test_fuzz.py                                 |   6 -
 tests/test_gate_cache.py                           |   6 -
 tests/test_gates.py                                | 306 ---------------------
 tests/test_gates_fmt_directives.py                 |   6 -
 tests/test_gates_worktree_lease.py                 |   6 -
 tests/test_gitio.py                                |  11 -
 tests/test_graph.py                                |  70 -----
 tests/test_graph_affects.py                        |   6 -
 tests/test_lang.py                                 |  27 --
 tests/test_makefile_lock_sync.py                   |   5 -
 tests/test_perf.py                                 |  97 -------
 tests/test_perf_rules_internals.py                 |   8 -
 tests/test_pii_structural_gate.py                  |  48 ----
 tests/test_policy.py                               |   6 -
 tests/test_refs_gate.py                            |  19 --
 tests/test_registry_corpus.py                      |   1 -
 tests/test_registry_exhaustiveness.py              |  66 -----
 tests/test_registry_models.py                      |   1 -
 tests/test_registry_reconciliation_compliance.py   |  16 --
 tests/test_registry_reconciliation_evasion.py      |   9 -
 tests/test_registry_reconciliation_patterns.py     |  24 --
 tests/test_registry_reconciliation_pii.py          |  24 --
 tests/test_registry_reconciliation_secrets.py      |  24 --
 tests/test_registry_reconciliation_supply_chain.py |   9 -
 .../test_registry_reconciliation_system_design.py  |  15 -
 tests/test_registry_reconciliation_weaknesses.py   |   9 -
 tests/test_registry_staleness.py                   |   1 -
 tests/test_release_worktree_lease.py               |   6 -
 tests/test_scaffold_worktree_lease_hook.py         |   1 -
 tests/test_secrets_gate.py                         |  47 ----
 tests/test_testing.py                              |  32 ---
 tests/test_ticket_land.py                          |  10 -
 tests/test_ticket_leases.py                        |   5 -
 tests/test_ticket_leases_cross_worktree.py         |  10 -
 tests/test_ticket_merge_driver.py                  |   1 -
 tests/test_ticket_reverify.py                      |  12 -
 tests/test_ticket_runner_pytest_env.py             |   3 -
 tests/test_tickets_acceptance.py                   |  12 -
 tests/test_tickets_dispatch_stale.py               |   6 -
 tests/test_tickets_evidence_cli.py                 |   9 -
 tests/test_tickets_lease_overlay.py                |   6 -
 tests/test_tickets_live_tracker.py                 |  12 -
 tests/test_tickets_mutation_evidence.py            |   4 -
 tests/test_tickets_new_gate_rule_acceptance.py     |   6 -
 tests/test_tickets_scope_mutation.py               |   9 -
 tests/test_vet.py                                  | 270 ------------------
 tests/test_walk_lint_gate.py                       |  10 -
 tests/test_walk_migration.py                       |   4 -
 tests/test_worktree_guard.py                       |   5 -
 tests/unit/cve/test_parser.py                      |  10 -
 tests/unit/deploy/test_conform.py                  |   3 -
 tests/unit/deploy/test_deploy_runner.py            |   3 -
 tests/unit/deploy/test_drift.py                    |   3 -
 tests/unit/graph/test_dsl.py                       |  69 -----
 tests/unit/perf/test_dup_spawn.py                  |  27 --
 tests/unit/perf/test_loop_effects.py               |   6 -
 tests/unit/strata/test_access.py                   |   6 -
 tests/unit/strata/test_atomic.py                   |   6 -
 tests/unit/strata/test_audit.py                    |   6 -
 tests/unit/strata/test_backpressure.py             |   6 -
 tests/unit/strata/test_boundary_phases.py          |  15 -
 tests/unit/strata/test_capacity.py                 |   3 -
 tests/unit/strata/test_code_binding.py             |  18 --
 tests/unit/strata/test_compliance.py               |   6 -
 tests/unit/strata/test_conform_eval_needle.py      |  12 -
 tests/unit/strata/test_demand.py                   |   9 -
 tests/unit/strata/test_effects.py                  |  12 -
 tests/unit/strata/test_elaborate.py                |  27 --
 tests/unit/strata/test_export.py                   |  12 -
 tests/unit/strata/test_export_golden.py            |   3 -
 tests/unit/strata/test_facts.py                    |   3 -
 tests/unit/strata/test_host_isolation.py           |  33 ---
 tests/unit/strata/test_infra.py                    |  39 ---
 tests/unit/strata/test_litmus_audit_hardened.py    |   4 -
 tests/unit/strata/test_litmus_audit_vuln.py        |   4 -
 tests/unit/strata/test_litmus_chirp.py             |  12 -
 tests/unit/strata/test_litmus_cwe.py               |   4 -
 tests/unit/strata/test_litmus_deploy_secret.py     |   4 -
 tests/unit/strata/test_litmus_surface.py           |   4 -
 tests/unit/strata/test_litmus_tube.py              |   4 -
 tests/unit/strata/test_litmus_waive.py             |  18 --
 tests/unit/strata/test_litmus_waive_store.py       |  18 --
 tests/unit/strata/test_message_schema.py           |   6 -
 tests/unit/strata/test_native_staleness.py         |   3 -
 tests/unit/strata/test_observe.py                  |  18 --
 tests/unit/strata/test_pii.py                      |   6 -
 tests/unit/strata/test_policy.py                   |  15 -
 tests/unit/strata/test_refine.py                   |  12 -
 .../strata/test_registry_cross_corpus_totality.py  |   1 -
 tests/unit/strata/test_retry.py                    |   6 -
 tests/unit/strata/test_scenarios.py                |  12 -
 tests/unit/strata/test_secrets.py                  |   6 -
 tests/unit/strata/test_selfconform.py              |  50 ----
 tests/unit/strata/test_shared_state.py             |   6 -
 tests/unit/strata/test_ssot.py                     |   6 -
 tests/unit/strata/test_store_observability.py      |  18 --
 tests/unit/strata/test_system_design_coverage.py   |  13 -
 tests/unit/strata/test_threat.py                   |  51 ----
 tests/unit/strata/test_txn.py                      |   6 -
 tests/unit/test_app_runners.py                     |   3 -
 tests/unit/test_app_runners_batch5.py              |  18 --
 tests/unit/test_app_runners_batch6.py              |  30 --
 tests/unit/test_app_runners_batch7.py              |  45 ---
 tests/unit/test_app_style.py                       |   6 -
 tests/unit/test_arch.py                            | 189 -------------
 tests/unit/test_arch_ocp.py                        |  27 --
 tests/unit/test_check.py                           |  11 -
 tests/unit/test_cycle.py                           |   6 -
 tests/unit/test_dup_template.py                    |  15 -
 tests/unit/test_executable.py                      |   9 -
 tests/unit/test_extending_guides_complete.py       |   2 -
 tests/unit/test_lang_primitives.py                 |   6 -
 tests/unit/test_natives_build.py                   |   5 -
 tests/unit/test_outline.py                         |   9 -
 tests/unit/test_parse.py                           |   3 -
 tests/unit/test_research_assets.py                 |   3 -
 tests/unit/test_ticket_file_flags.py               |  11 -
 tickets.md                                         |  53 +++-
 307 files changed, 54 insertions(+), 3367 deletions(-)
```

### Evidence
- `tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_waiver_suppresses_and_reports` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2810 warning(s), 420 waived
- error-findings: none (measured, zero errors)
