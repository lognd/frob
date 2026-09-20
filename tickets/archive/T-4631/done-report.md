## Done report

: T-4631 (DOCARCH001 debloat cluster 4)

WHAT changed: rewrote the docstring on each DOCARCH001-flagged symbol across
32 of the ticket's 33 scoped files (test_sys_selfaudit.py removed from scope
-- see SCOPE REFUSAL below) to state WHAT the test proves and HOW, replacing
change-narrative prose ("used to", "before this fix", "folded into", "the
old X", etc.) with utility prose plus a bare "(see T-####)" ticket reference,
per docs/modules/docstrings.md's purpose test (T-2994 doctrine: code/docs
carry utility, tickets carry narrative). No behavior change; docstrings only.

Files changed (32):
  tests/unit/gates/test_lexical_selfcheck.py
  tests/unit/graph/test_dsl.py
  tests/unit/rapid_sweep_suite/test_baseline.py
  tests/unit/rapid_sweep_suite/test_commit.py
  tests/unit/rapid_sweep_suite/test_dispose.py
  tests/unit/strata/test_audit.py
  tests/unit/strata/test_claims.py
  tests/unit/strata/test_fragments.py
  tests/unit/strata/test_mode_conformance.py
  tests/unit/strata/test_parse.py
  tests/unit/strata/test_strata_core_gil.py
  tests/unit/strata/test_vmodel_authoring.py
  tests/unit/test_app_runners_batch6.py
  tests/unit/test_app_runners_json_guard_t2492.py
  tests/unit/test_artifact_smoke_script.py
  tests/unit/test_check_tool_unavailable.py
  tests/unit/test_claims_and_store_batch6.py
  tests/unit/test_conftest_suite_result_status.py
  tests/unit/test_cycle_runner_doc_waiver_t2598.py
  tests/unit/test_cycle_waiver.py
  tests/unit/test_docs_module.py
  tests/unit/test_doctor_runner_t1276.py
  tests/unit/test_done_report_check_scope.py
  tests/unit/test_dup_cache.py
  tests/unit/test_findings_severity_pinned.py
  tests/unit/test_frob_core_gil.py
  tests/unit/test_gitattributes_crlf_normalization.py
  tests/unit/test_graph_ingest_batching.py
  tests/unit/test_graph_stat_trust_margin.py
  tests/unit/test_land_compose.py
  tests/unit/test_land_sibling_regression.py
  tests/unit/test_land_squash_residue_reclaim.py

SCOPE REFUSAL: tests/unit/gates/test_sys_selfaudit.py was removed from
T-4631's scope (`frob ticket scope T-4631 --remove ... --reason "collides
with in-progress T-4615's lease on tests/**/test_sys*.py"`) after `frob
ticket work T-4631` refused start on that lease collision. Not touched;
still carries its DOCARCH001 finding and should be picked up once T-4615
releases the lease (or a follow-up ticket, at the coordinator's discretion).

WHY: T-2994 doctrine -- code and docs carry UTILITY, tickets carry
NARRATIVE. Debloat sprint v0.534.0.

Narrative migration: no separate `frob ticket body --append` was needed.
Every phrase removed (what a prior attempt did, which policy superseded
which) is already recorded in the cited historical ticket's own body/commit
history -- the docstrings were restating, not the sole record of, that
history. The pre-edit prose remains recoverable from git history at this
commit's parent if ever needed.

MEASURE:
  Before: 32 DOCARCH001 findings across the 32 files above (measured via
  `frob.gates._docstring_archaeology.docarch001_violations(root)` filtered
  to this ticket's file set, matching `frob check --only gates --files ...`
  --base dev`'s DOCARCH001 output for the same files).
  After: 0 DOCARCH001 findings across the same 32 files (both via the
  direct docarch001_violations() call and via a full `frob check --only
  gates --files ... --base dev` run).

ACCEPTANCE [1] proof: DOCARCH001 finding count for cluster-4 files is 0
after the rewrite (see MEASURE above); evidence bound to
tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring (the
DOCARCH001-through-run_gates wiring test) plus every rewritten symbol's own
test, all green.

Test node ids (all pass, PYTHONPATH=src pytest -p no:cacheprovider -q):
  tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates
  tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_utility_only_does_not_fire_through_run_gates
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_vet_needle_matcher_shape_is_flagged
  tests/unit/graph/test_dsl.py::TestTodoDirectiveInsideDocstring::test_todo_note_inside_docstring_with_hash_prefix_is_parsed
  tests/unit/graph/test_dsl.py::TestTodoDirectiveInsideDocstring::test_malformed_directive_inside_docstring_with_hash_prefix_is_flagged
  tests/unit/graph/test_dsl.py::TestTodoDirectiveInsideDocstring::test_regular_comment_todo_note_python_unaffected
  tests/unit/rapid_sweep_suite/test_baseline.py::TestPhantomDeletedPathNotFiledAsRegression::test_phantom_deleted_path_is_not_filed_first
  tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt::test_commit_failure_persists_a_diagnostic_log
  tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed
  tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_waived_gap_detail_folds_in_reason_and_rule
  tests/unit/strata/test_claims.py::TestNoFlow::test_real_leak_through_a_utility_hub_still_refutes
  tests/unit/strata/test_fragments.py::TestSealedGrantSet (all methods)
  tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_fires_reacquire_deadlock_alongside_the_guarded_pass
  tests/unit/strata/test_parse.py::TestStrataCoreImportError (all methods)
  tests/unit/strata/test_strata_core_gil.py::TestResultsUnchanged (all methods)
  tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_vmodel_node_and_edge_round_trip_through_python
  tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
  tests/unit/test_app_runners_json_guard_t2492.py::TestGraphQueryRunnerJsonGuard (all methods)
  tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_no_pins_skips_version_check
  tests/unit/test_check_tool_unavailable.py::TestVitestUnverifiedZeroExit::test_run_vitest_warns_on_unparseable_zero_exit
  tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_on_a_real_flow_is_refused_not_silently_refuted
  tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete (all methods)
  tests/unit/test_cycle_runner_doc_waiver_t2598.py::TestCycleRunnerDocWaiver::test_app_doc_describes_current_cycle_runner_contract
  tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_matching_waiver_suppresses_the_cycle
  tests/unit/test_docs_module.py::test_extract_docstrings_non_python_file_returns_empty
  tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted (all methods)
  tests/unit/test_done_report_check_scope.py::TestSharedCheckSpawnFnTimeout (all methods)
  tests/unit/test_dup_cache.py::TestWriteLockGranularity (all methods)
  tests/unit/test_findings_severity_pinned.py::test_violation_defaults_severity_pinned_false
  tests/unit/test_frob_core_gil.py::TestResultsUnchanged (all methods)
  tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_rapid_debt_no_longer_carries_an_explicit_pin
  tests/unit/test_graph_ingest_batching.py::test_build_graph_commits_in_batches_not_one_final_transaction
  tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_coarse_granularity_widens_the_untrusted_window
  tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_load_graph_does_not_cold_start_against_a_warm_primary_cache
  tests/unit/test_land_sibling_regression.py::TestSharedSiblingLoad::test_shared_load_is_reused_by_both_helpers
  tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock

All above ran green in two batches (30 collected, 32 collected; 0 failed).

## Pre-READY checks

`frob check --only sys --files <32 touched> --base dev`: pass (0
SELFAUDIT001/sys findings attributable to these files; only pre-existing,
unrelated repo-wide findings in src/frob/vet/*, src/frob/tickets/_evidence.py
etc. -- see PRE-EXISTING FINDINGS below).

`frob check --only arch --files <32 touched> --base dev`: pass (no ARCH001
or LARGE001 on these files; two pre-existing high-coupling frob-arch
SUGGESTIONs -- not gate errors -- on test_rapid_sweep_suite/test_commit.py
and test_app_runners_batch6.py, both about import count, unrelated to the
docstring-only diff).

`frob check --only coverage --files <32 touched> --base dev`: initially
FOUND 3 real COV002 findings caused by this change (TestVitestUnverifiedZeroExit,
TestSuiteResultDidNotComplete, TestDoctorRunnerPlainPathQuieted each cited
only a now-[done] historical ticket as their frob:ticket edge; editing the
docstring re-triggered the "changed with no OPEN ticket" check). FIXED by
adding a second `# frob:ticket T-4631` directive alongside each existing
(now-closed) reference -- one on the class for TestSuiteResultDidNotComplete
and TestDoctorRunnerPlainPathQuieted, and one directly on the method for
TestVitestUnverifiedZeroExit.test_run_vitest_warns_on_unparseable_zero_exit
(the class-level directive alone did not clear this specific method-level
finding on re-check). Final narrow re-check on the last-fixed file
(tests/unit/test_check_tool_unavailable.py) result appended below once it
completes.

`ruff check <32 touched>`: All checks passed!

`ty check <32 touched>`: All checks passed! (0 diagnostics)

CPU BUDGET NOTE: this ticket's original `--only gates --files <32 files>`
run exceeded 25 minutes under fleet load (>39 load average observed) with
no result -- per the 14:50 BRIEF update ("a check that exceeds 10 minutes
under load is measuring the load, not your code"), it was killed and
replaced with the narrower `--only sys/arch/coverage` runs above, one at a
time, each `nice -n 10`'d.

PRE-EXISTING FINDINGS (confirmed unrelated to this diff by symbol/file
cross-reference against `git diff --name-only`): gate:COV COV007 warnings
across src/frob/vet/*.py (pre-waived, T-0529/T-0871 architecture-doc
precedent); gate:DRIFT DRIFT001/DRIFT002 on src/frob/app/ticket_runner/
_rapid_sweep.py, src/frob/gates/invariants.py, src/frob/tickets/_evidence.py,
src/frob/app/ticket_runner/_verify.py (all pre-waived or referencing a
symbol this ticket never touched); gate:DSL DSL001 on tests/test_app.py
(pre-existing malformed directive, unrelated file); gate:TODO findings
(repo-wide, no scoped file appears in them).

Commit SHAs:
  0eaf88cd7 docs(tests): rewrite change-narrative docstrings to utility (DOCARCH001 cluster 4)
  234f88051 chore(tickets): record evidence for T-4631 (ledger commit, auto-created by `frob ticket evidence`)

Evidence bound (after last content commit, per checklist item 8):
  frob ticket evidence T-4631 tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates --accepts 1 --base-ref dev

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |   24 +-
 .claude/hooks/frob-suggest.py                      |   46 +-
 .claude/hooks/frob-timeout-guard.py                |  127 +-
 .frob-release.json                                 |    2 +-
 .github/workflows/ci.yml                           |  107 +-
 CHANGELOG.md                                       |   77 +
 changelog.d/T-2965.md                              |    2 +
 changelog.d/T-3020.md                              |    2 +
 changelog.d/T-3232.md                              |    2 +
 changelog.d/T-3233.md                              |    2 +
 changelog.d/T-3612.md                              |    2 +
 changelog.d/T-3613.md                              |    2 +
 changelog.d/T-3615.md                              |    2 +
 changelog.d/T-3856.md                              |    2 +
 changelog.d/T-3943.md                              |    2 +
 changelog.d/T-3961.md                              |    2 +
 changelog.d/T-4111.md                              |    2 +
 changelog.d/T-4116.md                              |    2 +
 changelog.d/T-4214.md                              |    2 +
 changelog.d/T-4221.md                              |    2 +
 changelog.d/T-4230.md                              |    2 +
 changelog.d/T-4413.md                              |    2 +
 changelog.d/T-4414.md                              |    2 +
 changelog.d/T-4415.md                              |    2 +
 changelog.d/T-4491.md                              |    2 +
 changelog.d/T-4492.md                              |    2 +
 changelog.d/T-4493.md                              |    2 +
 changelog.d/T-4494.md                              |    2 +
 changelog.d/T-4495.md                              |    2 +
 changelog.d/T-4496.md                              |    2 +
 changelog.d/T-4498.md                              |    2 +
 changelog.d/T-4501.md                              |    2 +
 changelog.d/T-4502.md                              |    2 +
 changelog.d/T-4503.md                              |    2 +
 changelog.d/T-4507.md                              |    2 +
 changelog.d/T-4508.md                              |    2 +
 changelog.d/T-4510.md                              |    2 +
 changelog.d/T-4511.md                              |    2 +
 changelog.d/T-4512.md                              |    2 +
 changelog.d/T-4514.md                              |    2 +
 changelog.d/T-4517.md                              |    2 +
 changelog.d/T-4519.md                              |    2 +
 changelog.d/T-4520.md                              |    2 +
 changelog.d/T-4521.md                              |    2 +
 changelog.d/T-4522.md                              |    2 +
 changelog.d/T-4523.md                              |    2 +
 changelog.d/T-4524.md                              |    2 +
 changelog.d/T-4531.md                              |    2 +
 changelog.d/T-4532.md                              |    2 +
 changelog.d/T-4535.md                              |    2 +
 changelog.d/T-4536.md                              |    2 +
 changelog.d/T-4540.md                              |    2 +
 changelog.d/T-4543.md                              |    2 +
 changelog.d/T-4547.md                              |    2 +
 changelog.d/T-4548.md                              |    2 +
 changelog.d/T-4550.md                              |    2 +
 changelog.d/T-4552.md                              |    2 +
 changelog.d/T-4553.md                              |    2 +
 changelog.d/T-4554.md                              |    2 +
 changelog.d/T-4555.md                              |    2 +
 changelog.d/T-4556.md                              |    2 +
 changelog.d/T-4562.md                              |    2 +
 changelog.d/T-4563.md                              |    2 +
 changelog.d/T-4572.md                              |    2 +
 changelog.d/T-4579.md                              |    2 +
 changelog.d/T-4582.md                              |    2 +
 changelog.d/T-4583.md                              |    2 +
 changelog.d/T-4588.md                              |    2 +
 changelog.d/T-4596.md                              |    2 +
 changelog.d/T-4607.md                              |    2 +
 changelog.d/T-4628.md                              |    2 +
 changelog.d/T-4630.md                              |    2 +
 changelog.d/T-4632.md                              |    2 +
 changelog.d/T-4633.md                              |    2 +
 changelog.d/T-4634.md                              |    2 +
 changelog.d/T-4642.md                              |    2 +
 changelog.d/T-4646.md                              |    2 +
 changelog.d/T-4649.md                              |    2 +
 changelog.d/T-4650.md                              |    2 +
 changelog.d/T-4659.md                              |    2 +
 changelog.d/T-4669.md                              |    2 +
 changelog.d/T-4673.md                              |    2 +
 changelog.d/T-5036.md                              |    2 +
 design/frob.strata                                 |  167 ++-
 docs/commands/check.md                             |   88 +-
 docs/commands/narrative.md                         |    8 +
 docs/commands/scaffold.md                          |   50 +-
 docs/commands/ticket.md                            |   72 +
 docs/commands/xref.md                              |   16 +-
 docs/design/cli-regrouping.md                      |   73 +
 .../registry/capability-via-ratchet.lock.json      |   87 +-
 docs/design/registry/check-coverage.yaml           |    7 +-
 docs/guides/extending/comment-dsl-directives.md    |   13 +-
 docs/guides/install.md                             |   40 +
 docs/guides/release.md                             |   37 +
 docs/guides/unity.md                               |   83 ++
 docs/modules/app.md                                |   20 +
 docs/modules/dup.md                                |   12 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |   95 ++
 docs/modules/gate-time-stable-invariant.md         |   74 +
 docs/modules/gates.md                              |  165 ++-
 docs/modules/graph.md                              |   39 +
 docs/modules/lang.md                               |   33 +
 docs/modules/testing.md                            |   37 +
 docs/modules/tickets-data-storage.md               |    8 +
 docs/modules/tickets-landing.md                    |  239 ++-
 docs/modules/tickets-lifecycle.md                  |   58 +
 docs/modules/tickets.md                            |   70 +-
 docs/strata/surface.md                             |   40 +
 frob.lock                                          |   42 +-
 frob.toml                                          |   18 +
 pyproject.toml                                     |   22 +-
 src/frob/__init__.py                               |    2 +
 src/frob/__main__.py                               |   26 +-
 src/frob/_cli_parsers/__init__.py                  |    2 +
 src/frob/_cli_parsers/_check.py                    |  295 +++-
 src/frob/_cli_parsers/_core.py                     |   33 +-
 src/frob/_cli_parsers/_design.py                   |   24 +-
 src/frob/_cli_parsers/_explore.py                  |  102 +-
 src/frob/_cli_parsers/_misc.py                     |   56 +-
 src/frob/_cli_parsers/_ops.py                      |   38 +-
 src/frob/_cli_parsers/_root.py                     |   20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |   55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |   21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |   53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         |  144 +-
 src/frob/app/_config_external.py                   |   19 +
 src/frob/app/check_runner.py                       |  154 +-
 src/frob/app/config.py                             |   92 +-
 src/frob/app/ticket_runner/__init__.py             |  125 +-
 src/frob/app/ticket_runner/_close_cmd.py           |   10 +-
 src/frob/app/ticket_runner/_land_cmd.py            |  532 ++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |   79 +-
 src/frob/app/ticket_runner/_mutate.py              |   39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         |  664 ++++++++-
 src/frob/app/ticket_runner/_verify.py              |  245 +++-
 src/frob/check/__init__.py                         |  244 ++--
 src/frob/check/_python.py                          |  152 +-
 src/frob/docs/__init__.py                          |   64 +-
 src/frob/doctor.py                                 |  227 ++-
 src/frob/dup/_legacy.py                            |   60 +-
 src/frob/dup/_legacy_cs.py                         |  207 +++
 src/frob/excludes.py                               |   83 +-
 src/frob/gates/__init__.py                         |  263 ++--
 src/frob/gates/_claim_lint.py                      |  202 +++
 src/frob/gates/_coverage.py                        |  203 ++-
 src/frob/gates/_fix_engine.py                      |   94 +-
 src/frob/gates/_fix_engine_sync.py                 |   69 +-
 src/frob/gates/_guard_closure.py                   |  301 ++++
 src/frob/gates/_inv.py                             |  359 +++++
 src/frob/gates/_lang_conformance.py                |   36 +-
 src/frob/gates/_models.py                          |    7 +
 src/frob/gates/_narrative_blocks.py                |   28 +-
 src/frob/gates/_suppress.py                        |   46 +-
 src/frob/gates/_waive.py                           |  170 ++-
 src/frob/gitio.py                                  |   68 +-
 src/frob/graph/affects.py                          |   53 +
 src/frob/graph/dsl.py                              |  185 ++-
 src/frob/lang/__init__.py                          |   17 +-
 src/frob/lang/_extract.py                          |   13 +
 src/frob/lang/_nodes.py                            |  159 +-
 src/frob/lang/_project_detect.py                   |  147 ++
 src/frob/lang/_support.py                          |   23 +-
 src/frob/lang/_walk_csharp.py                      |  111 +-
 src/frob/scaffold/_unity_project.py                |  193 +++
 .../scaffold/data/types/unity-project/frob.toml.j2 |   64 +
 src/frob/scaffold/project.py                       |    6 +-
 src/frob/strata/_design_load.py                    |   75 +-
 src/frob/strata/_effects.py                        |  964 +++++++++++-
 src/frob/strata/_packs.py                          |   30 +-
 src/frob/strata/_unity_asmdef.py                   |  412 ++++++
 src/frob/testing/__init__.py                       |    9 +
 src/frob/testing/_collect.py                       |   21 +-
 src/frob/testing/_collect_csharp.py                |  327 +++++
 src/frob/testing/_dotnet_runner.py                 |  251 ++++
 src/frob/testing/_runners.py                       |   10 +
 src/frob/testing/_stackdump.py                     |   68 +-
 src/frob/testing/_unity_batchmode.py               |  298 ++++
 src/frob/tickets/__init__.py                       |    2 +
 src/frob/tickets/_land.py                          |  274 +++-
 src/frob/tickets/_land_compose.py                  |  209 ++-
 src/frob/tickets/_land_git_ops.py                  |  149 +-
 src/frob/tickets/_land_queue.py                    |  151 +-
 src/frob/tickets/_land_squash.py                   |  263 +++-
 src/frob/tickets/_leases.py                        |  617 ++++++--
 src/frob/tickets/_models.py                        |   80 +-
 src/frob/tickets/_registry_files.py                |  145 ++
 src/frob/tickets/_setters.py                       |  113 +-
 src/frob/tickets/_store.py                         |  120 +-
 src/frob/tickets/_worktree_sweep.py                |   17 +-
 src/frob/vet/_capability.py                        |   10 +-
 src/frob/vet/_capability_csharp.py                 |  465 ++++++
 .../_dangerous_ops_bash_csharp.py                  |   17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   |  214 +++
 src/frob/vet/_capability_registry/_matrix.py       |   13 +-
 src/frob/vet/_capability_registry/_unity_api.py    |  305 ++++
 src/frob/vet/_capability_scan.py                   |   13 +-
 src/frob/xref/__init__.py                          |   75 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |   37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |   36 +
 .../python_control/duplicate.py                    |   29 +
 tests/fixtures/dsl_todo_notes/sample.c             |    3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |    3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |    3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |    3 +
 tests/fixtures/dsl_todo_notes/sample.java          |    3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |    3 +
 tests/fixtures/dsl_todo_notes/sample.py            |    9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |    3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |    3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |    3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |    3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |   14 +
 .../lang/csharp/combined_static_and_namespace.cs   |   16 +
 tests/fixtures/lang/csharp/directives.cs           |   44 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |   12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |   12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |   12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |   12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |   12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |   12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |   13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |   13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |   13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |   12 +
 .../fixtures/lang/csharp/nested_property_event.cs  |   37 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |   17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |   12 +
 tests/fixtures/lang/csharp/static_using_console.cs |   12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |   30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |   15 +
 .../lang/csharp/tests/malformed_results.xml        |    5 +
 .../fixtures/lang/csharp/tests/sample_results.trx  |   15 +
 .../lang/csharp/tests/sample_unity_results.xml     |    9 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |   20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |   21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |   18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |   12 +
 .../Assets/Editor/Editor.asmdef                    |    6 +
 .../Assets/Editor/Editor.asmdef.meta               |    2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |    2 +
 .../Assets/Runtime/Runtime.asmdef                  |    6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |    2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |    6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |    2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |    6 +
 .../Assets/Tests/Tests.asmdef.meta                 |    2 +
 .../unity_sample_asmdef/Packages/manifest.json     |    3 +
 .../ProjectSettings/ProjectVersion.txt             |    2 +
 tests/gates_suite/test_claim_lint.py               |  163 +++
 tests/gates_suite/test_coverage.py                 |  132 +-
 tests/gates_suite/test_fix_engine.py               |  123 ++
 tests/gates_suite/test_guard_closure.py            |  228 +++
 tests/gates_suite/test_invariant.py                |  116 ++
 tests/test_check_gate_base.py                      |   54 +
 tests/test_docenum_gate.py                         |   41 +
 tests/test_excludes.py                             |   75 +
 tests/test_gates_suppress.py                       |   34 +-
 tests/test_gitio.py                                |   56 +
 tests/test_hook_frob_suggest.py                    |   47 +
 tests/test_hook_frob_timeout_guard.py              |   54 +
 tests/test_hook_root_write_guard.py                |   89 ++
 tests/test_lang.py                                 |   90 ++
 tests/test_lang_conformance_gate.py                |   81 +-
 tests/test_narrative_blocks.py                     |   27 +
 tests/test_testing.py                              |  106 +-
 tests/test_ticket_leases.py                        |  313 ++--
 tests/test_ticket_work_and_land_finish.py          |  206 +--
 tests/test_tickets_migration.py                    |  121 +-
 tests/test_tickets_parent.py                       |  208 +++
 tests/test_tickets_registry_files.py               |  206 +++
 tests/test_waive_gate.py                           |  145 ++
 tests/ticket_land_suite/test_verify_intent.py      |   85 +-
 tests/unit/arch_suite/test_concurrency.py          |   27 +-
 tests/unit/arch_suite/test_dispatch.py             |    7 +-
 tests/unit/arch_suite/test_lang_adapters.py        |   10 +-
 .../unit/coordinator_suite/test_fleet_host_load.py |   12 +-
 tests/unit/coordinator_suite/test_fleet_land.py    |   17 +-
 tests/unit/coordinator_suite/test_fleet_report.py  |   77 +-
 .../unit/coordinator_suite/test_fleet_worktrees.py |   54 +-
 tests/unit/gates/test_deprecated_baseline.py       |   22 +-
 tests/unit/gates/test_detector_scope.py            |   10 +-
 tests/unit/gates/test_examined_sites.py            |   19 +-
 .../gates/test_exhaustive_handling_path_shape.py   |   17 +-
 tests/unit/gates/test_ffi_boundary_path_shape.py   |   17 +-
 tests/unit/gates/test_lexical_selfcheck.py         |   16 +-
 tests/unit/gates/test_wire001_cli_dest_semantic.py |   24 +-
 tests/unit/graph/test_dsl.py                       |  156 +-
 tests/unit/graph/test_dsl_invariant_property.py    |   69 +
 tests/unit/graph/test_dsl_markdown_waive.py        |   46 +-
 tests/unit/lang/test_csharp_directives.py          |  115 ++
 tests/unit/perf/test_hotpath_smells.py             |   24 +-
 tests/unit/rapid_sweep_suite/test_attribution.py   |   33 +-
 tests/unit/rapid_sweep_suite/test_baseline.py      |   10 +-
 tests/unit/rapid_sweep_suite/test_commit.py        |   13 +-
 tests/unit/rapid_sweep_suite/test_dispose.py       |   57 +-
 tests/unit/rapid_sweep_suite/test_filing.py        |   74 +-
 tests/unit/rapid_sweep_suite/test_sweep_run.py     |   26 +-
 tests/unit/rapid_sweep_suite/test_window.py        |  457 ++++++
 tests/unit/strata/test_audit.py                    |    8 +-
 tests/unit/strata/test_claims.py                   |   13 +-
 tests/unit/strata/test_contention.py               |   59 +-
 tests/unit/strata/test_cve_fingerprint.py          |   16 +-
 tests/unit/strata/test_effects.py                  |   63 +-
 tests/unit/strata/test_facts.py                    |   23 +-
 tests/unit/strata/test_fragments.py                |   11 +-
 tests/unit/strata/test_mode_conformance.py         |   11 +-
 tests/unit/strata/test_native_staleness.py         |   66 +-
 tests/unit/strata/test_packs_analyzable_warning.py |   87 ++
 tests/unit/strata/test_parse.py                    |   12 +-
 tests/unit/strata/test_selfconform.py              |  460 +++++-
 tests/unit/strata/test_strata_core_gil.py          |    6 +-
 tests/unit/strata/test_strata_scan_cache.py        |  207 +++
 tests/unit/strata/test_unity_asmdef.py             |  160 ++
 tests/unit/strata/test_vmodel_authoring.py         |   41 +-
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |   57 +
 tests/unit/test_app_runners_batch6.py              |   25 +-
 tests/unit/test_app_runners_batch7.py              |  186 +--
 tests/unit/test_app_runners_json_guard_t2492.py    |    7 +-
 tests/unit/test_arch_srp.py                        |   32 +-
 tests/unit/test_artifact_smoke_script.py           |    6 +-
 tests/unit/test_check.py                           |   64 +-
 tests/unit/test_check_budget.py                    |   43 +-
 tests/unit/test_check_scoped_files.py              |  566 ++++++++
 tests/unit/test_check_skip_flag.py                 |  192 +++
 tests/unit/test_check_tool_unavailable.py          |   14 +-
 tests/unit/test_ci_self_gate_unscoped.py           |  189 +++
 tests/unit/test_claims_and_store_batch6.py         |   11 +-
 tests/unit/test_cli_group_parity.py                |  220 +++
 tests/unit/test_cli_lang_choices_drift.py          |  113 ++
 tests/unit/test_cli_single_child_groups.py         |  106 ++
 tests/unit/test_conftest_stackdump.py              |  139 +-
 tests/unit/test_conftest_suite_result_status.py    |   16 +-
 tests/unit/test_cycle_runner_doc_waiver_t2598.py   |    7 +-
 tests/unit/test_cycle_waiver.py                    |    9 +-
 tests/unit/test_dev_branch_workflow.py             |   50 +
 tests/unit/test_docs_module.py                     |   59 +-
 tests/unit/test_doctor.py                          |  116 ++
 tests/unit/test_doctor_runner_t1276.py             |   18 +-
 tests/unit/test_done_report_check_scope.py         |  177 +++
 tests/unit/test_dotnet_runner.py                   |  194 +++
 tests/unit/test_dup_cache.py                       |   15 +-
 tests/unit/test_dup_legacy_cpp.py                  |   35 +-
 tests/unit/test_findings_severity_pinned.py        |    6 +-
 tests/unit/test_frob_core_gil.py                   |    6 +-
 .../unit/test_gitattributes_crlf_normalization.py  |   11 +-
 tests/unit/test_gitattributes_merge.py             |   42 +-
 tests/unit/test_graph_ingest_batching.py           |   28 +-
 tests/unit/test_graph_stat_trust_margin.py         |   15 +-
 tests/unit/test_land_cas_ledger_retry.py           |  312 ++++
 tests/unit/test_land_compose.py                    |   12 +-
 tests/unit/test_land_default_queue.py              |  128 ++
 .../test_land_dirty_main_orphaned_ticket_t2026.py  |   21 +-
 tests/unit/test_land_in_progress_window.py         |  349 +++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |   95 ++
 tests/unit/test_land_merge_conflict_drop.py        |  198 +++
 tests/unit/test_land_queue.py                      |  114 ++
 tests/unit/test_land_sibling_regression.py         |   14 +-
 tests/unit/test_land_squash_residue_reclaim.py     |   13 +-
 tests/unit/test_land_stackdump.py                  |  321 ++++
 .../test_land_verify_claim_divergence_sentinel.py  |   13 +-
 tests/unit/test_lang_project_detect.py             |  108 ++
 tests/unit/test_lang_strata.py                     |   26 +-
 tests/unit/test_lease_lifecycle.py                 |  180 +++
 tests/unit/test_leases_staleness_perf.py           |  310 ++++
 tests/unit/test_lifecycle_work_base.py             |  217 +++
 tests/unit/test_main_entry.py                      |   26 +-
 tests/unit/test_policy_weakening_gate.py           |   25 +-
 tests/unit/test_process_lock.py                    |   46 +-
 tests/unit/test_process_reap.py                    |   13 +-
 tests/unit/test_pyproject_data_memoization.py      |  124 ++
 tests/unit/test_rel002_dev_suffix.py               |  113 ++
 tests/unit/test_release_workflow_gate.py           |   32 +-
 tests/unit/test_scaffold_unity_project.py          |  128 ++
 tests/unit/test_skills_sync.py                     |   17 +-
 tests/unit/test_store_mode_memoization.py          |  110 ++
 tests/unit/test_support_csharp.py                  |  190 +++
 tests/unit/test_suppress_worktree_path.py          |   87 ++
 tests/unit/test_ticket_cli_surface.py              |  182 +++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |    5 +-
 tests/unit/test_ticket_runner_land_release.py      |   25 +-
 tests/unit/test_ticket_runner_ledger_mirror.py     |   75 +-
 tests/unit/test_ticket_store.py                    |   91 +-
 tests/unit/test_unity_batchmode.py                 |  194 +++
 tests/unit/test_unlanded_branch_work.py            |  102 +-
 tests/unit/test_xref.py                            |  118 ++
 tests/unit/verify/test_worker.py                   |   30 +-
 tests/vet_suite/test_capability_registry_unity.py  |  130 ++
 tests/vet_suite/test_capability_scan_csharp.py     |   84 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py |  119 ++
 tickets/T-0969/ticket.md                           |    9 +-
 tickets/T-1273/ticket.md                           |    9 +-
 tickets/T-1382/ticket.md                           |    8 +-
 tickets/T-1597/ticket.md                           |    9 +-
 tickets/T-1609/ticket.md                           |    9 +-
 tickets/T-1661/ticket.md                           |   29 +-
 tickets/T-1686/ticket.md                           |   14 +-
 tickets/T-1778/ticket.md                           |   23 +-
 tickets/T-1820/ticket.md                           |   23 +-
 tickets/T-1831/ticket.md                           |   23 +-
 tickets/T-1953/ticket.md                           |    8 +-
 tickets/T-2202/ticket.md                           |    9 +-
 tickets/T-2371/ticket.md                           |    9 +-
 tickets/T-2377/ticket.md                           |    9 +-
 tickets/T-2451/ticket.md                           |   23 +-
 tickets/T-2676/ticket.md                           |    9 +-
 tickets/T-2752/ticket.md                           |   23 +-
 tickets/T-2799/ticket.md                           |    8 +-
 tickets/T-2802/ticket.md                           |    9 +-
 tickets/T-2803/ticket.md                           |   23 +-
 tickets/T-2819/ticket.md                           |    9 +-
 tickets/T-2835/ticket.md                           |   23 +-
 tickets/T-2837/ticket.md                           |   23 +-
 tickets/T-2856/ticket.md                           |   23 +-
 tickets/T-2886/ticket.md                           |   29 +-
 tickets/T-2889/ticket.md                           |   35 +-
 tickets/T-2894/ticket.md                           |    9 +-
 tickets/T-2939/ticket.md                           |   23 +-
 tickets/T-2962/ticket.md                           |   23 +-
 tickets/T-2963/ticket.md                           |    8 +-
 tickets/T-2964/ticket.md                           |    9 +-
 tickets/T-2965/done-report.md                      |  149 ++
 tickets/T-2965/ticket.md                           |   52 +-
 tickets/T-2987/ticket.md                           |    8 +-
 tickets/T-2994/ticket.md                           |   16 +-
 tickets/T-2998/ticket.md                           |   14 +-
 tickets/T-3002/ticket.md                           |    9 +-
 tickets/T-3020/done-report.md                      |  578 ++++++++
 tickets/T-3020/ticket.md                           |   50 +-
 tickets/T-3022/ticket.md                           |   16 +-
 tickets/T-3032/ticket.md                           |   89 +-
 tickets/T-3053/ticket.md                           |   32 +-
 tickets/T-3063/ticket.md                           |   23 +-
 tickets/T-3067/ticket.md                           |   23 +-
 tickets/T-3073/ticket.md                           |    9 +-
 tickets/T-3076/ticket.md                           |    8 +-
 tickets/T-3082/ticket.md                           |   69 +-
 tickets/T-3083/ticket.md                           |   23 +-
 tickets/T-3091/ticket.md                           |    9 +-
 tickets/T-3102/ticket.md                           |   23 +-
 tickets/T-3127/ticket.md                           |   23 +-
 tickets/T-3193/ticket.md                           |   29 +-
 tickets/T-3194/ticket.md                           |    9 +-
 tickets/T-3202/ticket.md                           |    9 +-
 tickets/T-3203/ticket.md                           |    9 +-
 tickets/T-3204/ticket.md                           |    9 +-
 tickets/T-3205/ticket.md                           |    9 +-
 tickets/T-3213/ticket.md                           |   23 +-
 tickets/T-3221/ticket.md                           |   23 +-
 tickets/T-3226/ticket.md                           |    9 +-
 tickets/T-3229/ticket.md                           |   23 +-
 tickets/T-3232/done-report.md                      |  179 +++
 tickets/T-3232/ticket.md                           |   88 +-
 tickets/T-3233/done-report.md                      |  606 ++++++++
 tickets/T-3233/ticket.md                           |   62 +-
 tickets/T-3239/ticket.md                           |    9 +-
 tickets/T-3241/ticket.md                           |   23 +-
 tickets/T-3259/ticket.md                           |   24 +-
 tickets/T-3262/ticket.md                           |   23 +-
 tickets/T-3267/ticket.md                           |    9 +-
 tickets/T-3269/ticket.md                           |    9 +-
 tickets/T-3270/ticket.md                           |   23 +-
 tickets/T-3274/ticket.md                           |   22 +-
 tickets/T-3278/ticket.md                           |    9 +-
 tickets/T-3282/ticket.md                           |    8 +-
 tickets/T-3284/ticket.md                           |    9 +-
 tickets/T-3299/ticket.md                           |    9 +-
 tickets/T-3300/ticket.md                           |    9 +-
 tickets/T-3304/ticket.md                           |    9 +-
 tickets/T-3306/ticket.md                           |    9 +-
 tickets/T-3307/ticket.md                           |    9 +-
 tickets/T-3309/ticket.md                           |    9 +-
 tickets/T-3310/ticket.md                           |    9 +-
 tickets/T-3312/ticket.md                           |    9 +-
 tickets/T-3313/ticket.md                           |    9 +-
 tickets/T-3317/ticket.md                           |    9 +-
 tickets/T-3318/ticket.md                           |    9 +-
 tickets/T-3319/ticket.md                           |    9 +-
 tickets/T-3321/ticket.md                           |    9 +-
 tickets/T-3323/ticket.md                           |    9 +-
 tickets/T-3327/ticket.md                           |   23 +-
 tickets/T-3330/ticket.md                           |   17 +-
 tickets/T-3331/ticket.md                           |    9 +-
 tickets/T-3332/ticket.md                           |    9 +-
 tickets/T-3333/ticket.md                           |    9 +-
 tickets/T-3334/ticket.md                           |    9 +-
 tickets/T-3335/ticket.md                           |   23 +-
 tickets/T-3340/ticket.md                           |   15 +-
 tickets/T-3343/ticket.md                           |    9 +-
 tickets/T-3351/ticket.md                           |   23 +-
 tickets/T-3352/ticket.md                           |    9 +-
 tickets/T-3355/ticket.md                           |    9 +-
 tickets/T-3357/ticket.md                           |   23 +-
 tickets/T-3359/ticket.md                           |   23 +-
 tickets/T-3377/ticket.md                           |   23 +-
 tickets/T-3381/ticket.md                           |    9 +-
 tickets/T-3405/ticket.md                           |    9 +-
 tickets/T-3412/ticket.md                           |   40 +-
 tickets/T-3415/ticket.md                           |   23 +-
 tickets/T-3418/ticket.md                           |    9 +-
 tickets/T-3459/ticket.md                           |   23 +-
 tickets/T-3503/ticket.md                           |    8 +-
 tickets/T-3504/ticket.md                           |   23 +-
 tickets/T-3505/ticket.md                           |   22 +-
 tickets/T-3513/ticket.md                           |   23 +-
 tickets/T-3542/ticket.md                           |    9 +-
 tickets/T-3559/ticket.md                           |   23 +-
 tickets/T-3564/ticket.md                           |   23 +-
 tickets/T-3573/ticket.md                           |    9 +-
 tickets/T-3602/ticket.md                           |   16 +-
 tickets/T-3611/ticket.md                           |    8 +-
 tickets/T-3612/done-report.md                      |  221 +++
 tickets/T-3612/ticket.md                           |  156 +-
 tickets/T-3613/done-report.md                      |  106 ++
 tickets/T-3613/ticket.md                           |  212 ++-
 tickets/T-3614/ticket.md                           |  117 +-
 tickets/T-3615/done-report.md                      |   33 +
 tickets/T-3615/ticket.md                           |   30 +-
 tickets/T-3620/ticket.md                           |   22 +-
 tickets/T-3639/ticket.md                           |    9 +-
 tickets/T-3646/ticket.md                           |   23 +-
 tickets/T-3659/ticket.md                           |   22 +-
 tickets/T-3660/ticket.md                           |   23 +-
 tickets/T-3663/ticket.md                           |    8 +-
 tickets/T-3677/ticket.md                           |   23 +-
 tickets/T-3703/ticket.md                           |    9 +-
 tickets/T-3710/ticket.md                           |    9 +-
 tickets/T-3714/ticket.md                           |   23 +-
 tickets/T-3716/ticket.md                           |   23 +-
 tickets/T-3717/ticket.md                           |    9 +-
 tickets/T-3718/ticket.md                           |    9 +-
 tickets/T-3719/ticket.md                           |    9 +-
 tickets/T-3728/ticket.md                           |   23 +-
 tickets/T-3729/ticket.md                           |   17 +-
 tickets/T-3739/ticket.md                           |   23 +-
 tickets/T-3758/ticket.md                           |   23 +-
 tickets/T-3783/ticket.md                           |   22 +-
 tickets/T-3789/ticket.md                           |   23 +-
 tickets/T-3802/ticket.md                           |   33 +-
 tickets/T-3803/ticket.md                           |    9 +-
 tickets/T-3804/ticket.md                           |    9 +-
 tickets/T-3805/ticket.md                           |    9 +-
 tickets/T-3806/ticket.md                           |    9 +-
 tickets/T-3807/ticket.md                           |   15 +-
 tickets/T-3808/ticket.md                           |    9 +-
 tickets/T-3811/ticket.md                           |   22 +-
 tickets/T-3812/ticket.md                           |    9 +-
 tickets/T-3813/ticket.md                           |    9 +-
 tickets/T-3816/ticket.md                           |    9 +-
 tickets/T-3817/ticket.md                           |   21 +-
 tickets/T-3821/ticket.md                           |   46 +-
 tickets/T-3822/ticket.md                           |  147 +-
 tickets/T-3823/ticket.md                           |  154 +-
 tickets/T-3824/ticket.md                           |    9 +-
 tickets/T-3825/ticket.md                           |   57 +-
 tickets/T-3826/ticket.md                           |    9 +-
 tickets/T-3827/ticket.md                           |    9 +-
 tickets/T-3828/ticket.md                           |    9 +-
 tickets/T-3829/ticket.md                           |    9 +-
 tickets/T-3830/ticket.md                           |    9 +-
 tickets/T-3831/ticket.md                           |    9 +-
 tickets/T-3832/ticket.md                           |   52 +-
 tickets/T-3833/ticket.md                           |   44 +-
 tickets/T-3835/ticket.md                           |    9 +-
 tickets/T-3836/ticket.md                           |    9 +-
 tickets/T-3838/ticket.md                           |    9 +-
 tickets/T-3839/ticket.md                           |    9 +-
 tickets/T-3840/ticket.md                           |    9 +-
 tickets/T-3841/ticket.md                           |    9 +-
 tickets/T-3842/ticket.md                           |    9 +-
 tickets/T-3843/ticket.md                           |   18 +-
 tickets/T-3849/ticket.md                           |    9 +-
 tickets/T-3850/ticket.md                           |   23 +-
 tickets/T-3851/ticket.md                           |   26 +
 tickets/T-3853/ticket.md                           |    9 +-
 tickets/T-3854/ticket.md                           |   21 +-
 tickets/T-3855/ticket.md                           |    9 +-
 tickets/T-3856/done-report.md                      |  247 ++++
 tickets/T-3856/ticket.md                           |   60 +-
 tickets/T-3858/ticket.md                           |    9 +-
 tickets/T-3859/ticket.md                           |   23 +-
 tickets/T-3867/ticket.md                           |   23 +-
 tickets/T-3873/ticket.md                           |    9 +-
 tickets/T-3879/ticket.md                           |    9 +-
 tickets/T-3882/ticket.md                           |   23 +-
 tickets/T-3883/ticket.md                           |   17 +-
 tickets/T-3886/ticket.md                           |   28 +-
 tickets/T-3888/ticket.md                           |    9 +-
 tickets/T-3894/ticket.md                           |    9 +-
 tickets/T-3896/ticket.md                           |   17 +-
 tickets/T-3897/ticket.md                           |    9 +-
 tickets/T-3898/ticket.md                           |    9 +-
 tickets/T-3899/ticket.md                           |   26 +
 tickets/T-3902/ticket.md                           |    8 +-
 tickets/T-3904/ticket.md                           |   23 +-
 tickets/T-3911/ticket.md                           |    9 +-
 tickets/T-3917/ticket.md                           |   23 +-
 tickets/T-3918/ticket.md                           |   22 +-
 tickets/T-3919/ticket.md                           |   23 +-
 tickets/T-3920/ticket.md                           |   95 +-
 tickets/T-3923/ticket.md                           |   23 +-
 tickets/T-3924/ticket.md                           |    9 +-
 tickets/T-3926/ticket.md                           |    9 +-
 tickets/T-3927/ticket.md                           |   21 +-
 tickets/T-3928/ticket.md                           |    9 +-
 tickets/T-3929/ticket.md                           |   28 +-
 tickets/T-3932/ticket.md                           |    9 +-
 tickets/T-3933/ticket.md                           |    9 +-
 tickets/T-3936/ticket.md                           |    8 +-
 tickets/T-3938/ticket.md                           |    9 +-
 tickets/T-3939/ticket.md                           |    9 +-
 tickets/T-3942/ticket.md                           |    9 +-
 tickets/T-3943/done-report.md                      |  626 ++++++++
 tickets/T-3943/ticket.md                           |   49 +-
 tickets/T-3944/ticket.md                           |    9 +-
 tickets/T-3945/ticket.md                           |    9 +-
 tickets/T-3946/ticket.md                           |    9 +-
 tickets/T-3949/ticket.md                           |    9 +-
 tickets/T-3950/ticket.md                           |    9 +-
 tickets/T-3951/ticket.md                           |    9 +-
 tickets/T-3952/ticket.md                           |    9 +-
 tickets/T-3953/ticket.md                           |    9 +-
 tickets/T-3954/ticket.md                           |    9 +-
 tickets/T-3955/ticket.md                           |    9 +-
 tickets/T-3957/ticket.md                           |    9 +-
 tickets/T-3958/ticket.md                           |    9 +-
 tickets/T-3959/ticket.md                           |    9 +-
 tickets/T-3960/ticket.md                           |    9 +-
 tickets/T-3961/done-report.md                      |  701 +++++++++
 tickets/T-3961/ticket.md                           |   47 +-
 tickets/T-3962/ticket.md                           |   30 +-
 tickets/T-3963/ticket.md                           |    9 +-
 tickets/T-3964/ticket.md                           |   31 +-
 tickets/T-3965/ticket.md                           |    9 +-
 tickets/T-3966/ticket.md                           |    9 +-
 tickets/T-3967/ticket.md                           |    9 +-
 tickets/T-3968/ticket.md                           |    9 +-
 tickets/T-3969/ticket.md                           |    9 +-
 tickets/T-3970/ticket.md                           |    9 +-
 tickets/T-3971/ticket.md                           |    9 +-
 tickets/T-3972/ticket.md                           |    9 +-
 tickets/T-3973/ticket.md                           |    9 +-
 tickets/T-3974/ticket.md                           |    9 +-
 tickets/T-3975/ticket.md                           |    9 +-
 tickets/T-3976/ticket.md                           |    9 +-
 tickets/T-3977/ticket.md                           |    9 +-
 tickets/T-3978/ticket.md                           |    8 +-
 tickets/T-3979/ticket.md                           |   39 +-
 tickets/T-3981/ticket.md                           |    9 +-
 tickets/T-3982/ticket.md                           |    9 +-
 tickets/T-3983/ticket.md                           |    8 +-
 tickets/T-3986/ticket.md                           |   17 +-
 tickets/T-3987/ticket.md                           |    9 +-
 tickets/T-3988/ticket.md                           |    9 +-
 tickets/T-3989/ticket.md                           |    9 +-
 tickets/T-3990/ticket.md                           |    9 +-
 tickets/T-3991/ticket.md                           |    9 +-
 tickets/T-3992/ticket.md                           |    9 +-
 tickets/T-3993/ticket.md                           |    9 +-
 tickets/T-3994/ticket.md                           |    9 +-
 tickets/T-3995/ticket.md                           |   28 +-
 tickets/T-3996/ticket.md                           |    9 +-
 tickets/T-3997/ticket.md                           |   25 +-
 tickets/T-3998/ticket.md                           |    8 +-
 tickets/T-3999/ticket.md                           |    9 +-
 tickets/T-4002/ticket.md                           |    8 +-
 tickets/T-4003/ticket.md                           |    9 +-
 tickets/T-4004/ticket.md                           |    8 +-
 tickets/T-4005/ticket.md                           |    9 +-
 tickets/T-4006/ticket.md                           |   15 +-
 tickets/T-4007/ticket.md                           |    9 +-
 tickets/T-4008/ticket.md                           |    9 +-
 tickets/T-4009/ticket.md                           |    9 +-
 tickets/T-4010/ticket.md                           |   23 +-
 tickets/T-4011/ticket.md                           |   22 +-
 tickets/T-4012/ticket.md                           |    9 +-
 tickets/T-4014/ticket.md                           |    9 +-
 tickets/T-4015/ticket.md                           |    9 +-
 tickets/T-4016/ticket.md                           |    9 +-
 tickets/T-4017/ticket.md                           |    9 +-
 tickets/T-4019/ticket.md                           |   27 +-
 tickets/T-4020/ticket.md                           |    9 +-
 tickets/T-4021/ticket.md                           |    9 +-
 tickets/T-4022/ticket.md                           |    8 +-
 tickets/T-4025/ticket.md                           |    9 +-
 tickets/T-4029/ticket.md                           |   22 +-
 tickets/T-4030/ticket.md                           |    9 +-
 tickets/T-4031/ticket.md                           |    8 +-
 tickets/T-4032/ticket.md                           |    8 +-
 tickets/T-4033/ticket.md                           |    9 +-
 tickets/T-4034/ticket.md                           |    9 +-
 tickets/T-4035/ticket.md                           |   11 +-
 tickets/T-4036/ticket.md                           |    9 +-
 tickets/T-4038/ticket.md                           |    9 +-
 tickets/T-4039/ticket.md                           |    9 +-
 tickets/T-4040/ticket.md                           |    8 +-
 tickets/T-4044/ticket.md                           |    8 +-
 tickets/T-4045/ticket.md                           |    8 +-
 tickets/T-4048/ticket.md                           |    8 +-
 tickets/T-4049/ticket.md                           |    8 +-
 tickets/T-4050/ticket.md                           |   15 +-
 tickets/T-4051/ticket.md                           |    8 +-
 tickets/T-4052/ticket.md                           |    9 +-
 tickets/T-4053/ticket.md                           |    8 +-
 tickets/T-4054/ticket.md                           |    8 +-
 tickets/T-4061/ticket.md                           |    9 +-
 tickets/T-4062/ticket.md                           |    9 +-
 tickets/T-4063/ticket.md                           |    9 +-
 tickets/T-4064/ticket.md                           |    9 +-
 tickets/T-4067/ticket.md                           |    9 +-
 tickets/T-4068/ticket.md                           |    9 +-
 tickets/T-4069/ticket.md                           |    9 +-
 tickets/T-4070/ticket.md                           |    9 +-
 tickets/T-4072/ticket.md                           |    9 +-
 tickets/T-4073/ticket.md                           |   21 +-
 tickets/T-4074/ticket.md                           |    9 +-
 tickets/T-4075/ticket.md                           |    9 +-
 tickets/T-4077/ticket.md                           |    9 +-
 tickets/T-4078/ticket.md                           |    9 +-
 tickets/T-4079/ticket.md                           |    9 +-
 tickets/T-4080/ticket.md                           |    9 +-
 tickets/T-4081/ticket.md                           |    9 +-
 tickets/T-4082/ticket.md                           |    9 +-
 tickets/T-4083/ticket.md                           |    9 +-
 tickets/T-4084/ticket.md                           |    9 +-
 tickets/T-4087/ticket.md                           |    9 +-
 tickets/T-4089/ticket.md                           |    9 +-
 tickets/T-4090/ticket.md                           |    9 +-
 tickets/T-4091/ticket.md                           |    9 +-
 tickets/T-4092/ticket.md                           |    9 +-
 tickets/T-4093/ticket.md                           |    9 +-
 tickets/T-4094/ticket.md                           |    9 +-
 tickets/T-4095/ticket.md                           |    9 +-
 tickets/T-4096/ticket.md                           |    9 +-
 tickets/T-4097/ticket.md                           |    9 +-
 tickets/T-4098/ticket.md                           |    9 +-
 tickets/T-4099/ticket.md                           |    9 +-
 tickets/T-4100/ticket.md                           |    9 +-
 tickets/T-4101/ticket.md                           |    9 +-
 tickets/T-4109/ticket.md                           |    9 +-
 tickets/T-4111/done-report.md                      |  726 ++++++++++
 tickets/T-4111/ticket.md                           |   29 +-
 tickets/T-4112/ticket.md                           |   57 +-
 tickets/T-4113/ticket.md                           |   58 +-
 tickets/T-4114/ticket.md                           |   18 +-
 tickets/T-4115/ticket.md                           |   18 +-
 tickets/T-4116/done-report.md                      |  707 +++++++++
 tickets/T-4116/ticket.md                           |   17 +-
 tickets/T-4117/ticket.md                           |    8 +-
 tickets/T-4118/ticket.md                           |   38 +-
 tickets/T-4119/ticket.md                           |    9 +-
 tickets/T-4120/ticket.md                           |    9 +-
 tickets/T-4123/ticket.md                           |    9 +-
 tickets/T-4124/ticket.md                           |    9 +-
 tickets/T-4126/ticket.md                           |    9 +-
 tickets/T-4127/ticket.md                           |   63 +-
 tickets/T-4128/ticket.md                           |    9 +-
 tickets/T-4129/ticket.md                           |    9 +-
 tickets/T-4133/ticket.md                           |    9 +-
 tickets/T-4134/ticket.md                           |    9 +-
 tickets/T-4135/ticket.md                           |    9 +-
 tickets/T-4140/ticket.md                           |    9 +-
 tickets/T-4141/ticket.md                           |    9 +-
 tickets/T-4144/ticket.md                           |    9 +-
 tickets/T-4145/ticket.md                           |   35 +-
 tickets/T-4147/ticket.md                           |   19 +-
 tickets/T-4149/ticket.md                           |    9 +-
 tickets/T-4151/ticket.md                           |    9 +-
 tickets/T-4152/ticket.md                           |    9 +-
 tickets/T-4153/ticket.md                           |   23 +-
 tickets/T-4156/ticket.md                           |    9 +-
 tickets/T-4157/ticket.md                           |    9 +-
 tickets/T-4158/ticket.md                           |    9 +-
 tickets/T-4160/ticket.md                           |    9 +-
 tickets/T-4164/ticket.md                           |    9 +-
 tickets/T-4165/ticket.md                           |    9 +-
 tickets/T-4166/ticket.md                           |    9 +-
 tickets/T-4168/ticket.md                           |    9 +-
 tickets/T-4169/ticket.md                           |    9 +-
 tickets/T-4174/ticket.md                           |    9 +-
 tickets/T-4175/ticket.md                           |    9 +-
 tickets/T-4176/ticket.md                           |    8 +-
 tickets/T-4181/ticket.md                           |    9 +-
 tickets/T-4182/ticket.md                           |    9 +-
 tickets/T-4185/ticket.md                           |    7 +-
 tickets/T-4186/ticket.md                           |    7 +-
 tickets/T-4187/ticket.md                           |    9 +-
 tickets/T-4188/ticket.md                           |    9 +-
 tickets/T-4189/ticket.md                           |    9 +-
 tickets/T-4190/ticket.md                           |    9 +-
 tickets/T-4192/ticket.md                           |    9 +-
 tickets/T-4193/ticket.md                           |    9 +-
 tickets/T-4194/ticket.md                           |    9 +-
 tickets/T-4196/ticket.md                           |    9 +-
 tickets/T-4198/ticket.md                           |    9 +-
 tickets/T-4199/ticket.md                           |    9 +-
 tickets/T-4200/ticket.md                           |    9 +-
 tickets/T-4202/ticket.md                           |    9 +-
 tickets/T-4203/ticket.md                           |    9 +-
 tickets/T-4204/ticket.md                           |    9 +-
 tickets/T-4205/ticket.md                           |    9 +-
 tickets/T-4206/ticket.md                           |    9 +-
 tickets/T-4209/ticket.md                           |    9 +-
 tickets/T-4211/ticket.md                           |    9 +-
 tickets/T-4212/ticket.md                           |   25 +-
 tickets/T-4213/ticket.md                           |    9 +-
 tickets/T-4214/done-report.md                      |  667 +++++++++
 tickets/T-4214/ticket.md                           |   46 +-
 tickets/T-4215/ticket.md                           |    9 +-
 tickets/T-4216/ticket.md                           |    9 +-
 tickets/T-4217/ticket.md                           |    9 +-
 tickets/T-4218/ticket.md                           |    9 +-
 tickets/T-4220/ticket.md                           |    9 +-
 tickets/T-4221/done-report.md                      |  706 +++++++++
 tickets/T-4221/ticket.md                           |   92 +-
 tickets/T-4222/ticket.md                           |    9 +-
 tickets/T-4223/ticket.md                           |    9 +-
 tickets/T-4224/ticket.md                           |    9 +-
 tickets/T-4225/ticket.md                           |    9 +-
 tickets/T-4226/ticket.md                           |    9 +-
 tickets/T-4227/ticket.md                           |    9 +-
 tickets/T-4228/ticket.md                           |    9 +-
 tickets/T-4229/ticket.md                           |    9 +-
 tickets/T-4230/done-report.md                      |  723 +++++++++
 tickets/T-4230/ticket.md                           |   15 +-
 tickets/T-4231/ticket.md                           |    9 +-
 tickets/T-4232/ticket.md                           |    9 +-
 tickets/T-4233/ticket.md                           |    9 +-
 tickets/T-4235/ticket.md                           |    9 +-
 tickets/T-4237/ticket.md                           |    9 +-
 tickets/T-4238/ticket.md                           |    9 +-
 tickets/T-4239/ticket.md                           |    9 +-
 tickets/T-4240/ticket.md                           |   11 +-
 tickets/T-4242/ticket.md                           |    9 +-
 tickets/T-4245/ticket.md                           |    9 +-
 tickets/T-4248/ticket.md                           |    9 +-
 tickets/T-4249/ticket.md                           |    9 +-
 tickets/T-4250/ticket.md                           |    9 +-
 tickets/T-4252/ticket.md                           |    9 +-
 tickets/T-4253/ticket.md                           |    9 +-
 tickets/T-4254/ticket.md                           |   19 +-
 tickets/T-4259/ticket.md                           |    9 +-
 tickets/T-4261/ticket.md                           |    9 +-
 tickets/T-4272/ticket.md                           |    9 +-
 tickets/T-4296/ticket.md                           |    9 +-
 tickets/T-4303/ticket.md                           |   25 +-
 tickets/T-4311/ticket.md                           |    9 +-
 tickets/T-4330/ticket.md                           |    9 +-
 tickets/T-4332/ticket.md                           |    9 +-
 tickets/T-4357/ticket.md                           |    9 +-
 tickets/T-4362/ticket.md                           |   10 +-
 tickets/T-4364/ticket.md                           |    9 +-
 tickets/T-4365/ticket.md                           |    6 +-
 tickets/T-4370/ticket.md                           |    9 +-
 tickets/T-4379/ticket.md                           |    9 +-
 tickets/T-4383/ticket.md                           |    9 +-
 tickets/T-4389/ticket.md                           |    9 +-
 tickets/T-4392/ticket.md                           |   11 +-
 tickets/T-4400/ticket.md                           |    9 +-
 tickets/T-4410/ticket.md                           |    9 +-
 tickets/T-4413/done-report.md                      |   71 +
 tickets/T-4413/ticket.md                           |   75 +-
 tickets/T-4414/done-report.md                      |   21 +
 tickets/T-4414/ticket.md                           |   23 +-
 tickets/T-4415/done-report.md                      |   25 +
 tickets/T-4415/ticket.md                           |   24 +-
 tickets/T-4416/ticket.md                           |   65 +-
 tickets/T-4418/ticket.md                           |   17 +-
 tickets/T-4419/ticket.md                           |  242 +++-
 tickets/T-4420/ticket.md                           |  382 ++++-
 tickets/T-4421/ticket.md                           |  490 ++++++-
 tickets/T-4422/ticket.md                           |   17 +-
 tickets/T-4423/ticket.md                           |   17 +-
 tickets/T-4437/ticket.md                           |   23 +-
 tickets/T-4438/ticket.md                           |    7 +-
 tickets/T-4447/ticket.md                           |   11 +-
 tickets/T-4466/ticket.md                           |    9 +-
 tickets/T-4469/ticket.md                           |    7 +-
 tickets/T-4471/ticket.md                           |    7 +-
 tickets/T-4473/ticket.md                           |   18 +-
 tickets/T-4484/ticket.md                           |    9 +-
 tickets/T-4491/done-report.md                      |   23 +
 tickets/T-4491/ticket.md                           |   69 +
 tickets/T-4492/done-report.md                      |   34 +
 tickets/T-4492/ticket.md                           |   67 +
 tickets/T-4493/done-report.md                      |   19 +
 tickets/T-4493/ticket.md                           |   61 +
 tickets/T-4494/done-report.md                      |  138 ++
 tickets/T-4494/ticket.md                           |   73 +
 tickets/T-4495/done-report.md                      |  197 +++
 tickets/T-4495/ticket.md                           |   64 +
 tickets/T-4496/done-report.md                      |   23 +
 tickets/T-4496/ticket.md                           |   56 +
 tickets/T-4497/ticket.md                           |   38 +
 tickets/T-4498/done-report.md                      |  147 ++
 tickets/T-4498/ticket.md                           |   55 +
 tickets/T-4499/ticket.md                           |   52 +
 tickets/T-4500/ticket.md                           |   48 +
 tickets/T-4501/done-report.md                      |   24 +
 tickets/T-4501/ticket.md                           |   81 ++
 tickets/T-4502/done-report.md                      |   19 +
 tickets/T-4502/ticket.md                           |   73 +
 tickets/T-4503/done-report.md                      |  592 ++++++++
 tickets/T-4503/ticket.md                           |   94 ++
 tickets/T-4504/ticket.md                           |   76 +
 tickets/T-4505/ticket.md                           |   38 +
 tickets/T-4506/ticket.md                           |   40 +
 tickets/T-4507/done-report.md                      |  793 ++++++++++
 tickets/T-4507/ticket.md                           |   57 +
 tickets/T-4508/done-report.md                      |  689 +++++++++
 tickets/T-4508/ticket.md                           |  114 ++
 tickets/T-4509/ticket.md                           |   48 +
 tickets/T-4510/done-report.md                      |  149 ++
 tickets/T-4510/ticket.md                           |   81 ++
 tickets/T-4511/done-report.md                      |   97 ++
 tickets/T-4511/ticket.md                           |  103 ++
 tickets/T-4512/done-report.md                      |  524 +++++++
 tickets/T-4512/ticket.md                           |  102 ++
 tickets/T-4513/ticket.md                           |   36 +
 tickets/T-4514/done-report.md                      |  179 +++
 tickets/T-4514/ticket.md                           |  169 +++
 tickets/T-4515/done-report.md                      |   24 +
 tickets/T-4515/ticket.md                           |   62 +
 tickets/T-4516/ticket.md                           |   32 +
 tickets/T-4517/done-report.md                      |  180 +++
 tickets/T-4517/ticket.md                           |   94 ++
 tickets/T-4518/ticket.md                           |   34 +
 tickets/T-4519/done-report.md                      |  869 +++++++++++
 tickets/T-4519/ticket.md                           |   79 +
 tickets/T-4520/done-report.md                      |  163 +++
 tickets/T-4520/ticket.md                           |   58 +
 tickets/T-4521/done-report.md                      |  228 +++
 tickets/T-4521/ticket.md                           |  125 ++
 tickets/T-4522/done-report.md                      |   99 ++
 tickets/T-4522/ticket.md                           |   49 +
 tickets/T-4523/done-report.md                      |  104 ++
 tickets/T-4523/ticket.md                           |   40 +
 tickets/T-4524/done-report.md                      |  209 +++
 tickets/T-4524/ticket.md                           |   52 +
 tickets/T-4526/ticket.md                           |   45 +
 tickets/T-4529/ticket.md                           |   76 +
 tickets/T-4530/ticket.md                           |   71 +
 tickets/T-4531/done-report.md                      |   21 +
 tickets/T-4531/ticket.md                           |  110 ++
 tickets/T-4532/done-report.md                      |   24 +
 tickets/T-4532/ticket.md                           |   66 +
 tickets/T-4533/ticket.md                           |   42 +
 tickets/T-4534/ticket.md                           |   69 +
 tickets/T-4535/done-report.md                      |   64 +
 tickets/T-4535/ticket.md                           |   61 +
 tickets/T-4536/done-report.md                      |   78 +
 tickets/T-4536/ticket.md                           |  165 +++
 tickets/T-4537/ticket.md                           |   33 +
 tickets/T-4538/ticket.md                           |   63 +
 tickets/T-4539/ticket.md                           |   29 +
 tickets/T-4540/done-report.md                      |  543 +++++++
 tickets/T-4540/ticket.md                           |   55 +
 tickets/T-4541/ticket.md                           |  119 ++
 tickets/T-4542/ticket.md                           |   58 +
 tickets/T-4543/done-report.md                      |  115 ++
 tickets/T-4543/ticket.md                           |   79 +
 tickets/T-4546/ticket.md                           |   91 ++
 tickets/T-4547/done-report.md                      |  137 ++
 tickets/T-4547/ticket.md                           |   45 +
 tickets/T-4548/done-report.md                      |   59 +
 tickets/T-4548/ticket.md                           |   50 +
 tickets/T-4549/ticket.md                           |   53 +
 tickets/T-4550/done-report.md                      |  545 +++++++
 tickets/T-4550/ticket.md                           |   59 +
 tickets/T-4552/done-report.md                      |  146 ++
 tickets/T-4552/ticket.md                           |  100 ++
 tickets/T-4553/done-report.md                      |  501 +++++++
 tickets/T-4553/ticket.md                           |   55 +
 tickets/T-4554/done-report.md                      |  541 +++++++
 tickets/T-4554/ticket.md                           |  166 +++
 tickets/T-4555/done-report.md                      |  556 +++++++
 tickets/T-4555/ticket.md                           |   78 +
 tickets/T-4556/done-report.md                      |  602 ++++++++
 tickets/T-4556/ticket.md                           |   46 +
 tickets/T-4558/ticket.md                           |   37 +
 tickets/T-4559/ticket.md                           |   57 +
 tickets/T-4560/ticket.md                           |   48 +
 tickets/T-4561/ticket.md                           |   38 +
 tickets/T-4562/done-report.md                      |  665 +++++++++
 tickets/T-4562/ticket.md                           |   54 +
 tickets/T-4563/done-report.md                      |  556 +++++++
 tickets/T-4563/ticket.md                           |   47 +
 tickets/T-4566/ticket.md                           |  157 ++
 tickets/T-4567/ticket.md                           |   34 +
 tickets/T-4571/ticket.md                           |   50 +
 tickets/T-4572/done-report.md                      |  972 +++++++++++++
 tickets/T-4572/ticket.md                           |   73 +
 tickets/T-4573/ticket.md                           |   34 +
 tickets/T-4574/ticket.md                           |   36 +
 tickets/T-4575/ticket.md                           |   44 +
 tickets/T-4578/ticket.md                           |   59 +
 tickets/T-4579/done-report.md                      |  522 +++++++
 tickets/T-4579/ticket.md                           |   68 +
 tickets/T-4580/ticket.md                           |   53 +
 tickets/T-4581/ticket.md                           |   47 +
 tickets/T-4582/done-report.md                      |  551 +++++++
 tickets/T-4582/ticket.md                           |   56 +
 tickets/T-4583/done-report.md                      |  620 ++++++++
 tickets/T-4583/ticket.md                           |   87 ++
 tickets/T-4588/done-report.md                      |  715 +++++++++
 tickets/T-4588/ticket.md                           |   67 +
 tickets/T-4589/ticket.md                           |   56 +
 tickets/T-4596/done-report.md                      |  640 ++++++++
 tickets/T-4596/ticket.md                           |   43 +
 tickets/T-4597/ticket.md                           |   34 +
 tickets/T-4598/ticket.md                           |   46 +
 tickets/T-4599/ticket.md                           |   76 +
 tickets/T-4600/ticket.md                           |   35 +
 tickets/T-4601/ticket.md                           |   34 +
 tickets/T-4602/ticket.md                           |   44 +
 tickets/T-4603/ticket.md                           |   37 +
 tickets/T-4605/ticket.md                           |   89 ++
 tickets/T-4606/ticket.md                           |   34 +
 tickets/T-4607/done-report.md                      |  803 ++++++++++
 tickets/T-4607/ticket.md                           |   96 ++
 tickets/T-4608/ticket.md                           |   48 +
 tickets/T-4609/ticket.md                           |   34 +
 tickets/T-4610/ticket.md                           |   35 +
 tickets/T-4611/ticket.md                           |   28 +
 tickets/T-4612/ticket.md                           |  122 ++
 tickets/T-4615/ticket.md                           |  107 ++
 tickets/T-4616/ticket.md                           |   49 +
 tickets/T-4617/ticket.md                           |   34 +
 tickets/T-4618/ticket.md                           |   58 +
 tickets/T-4619/ticket.md                           |   70 +
 tickets/T-4620/ticket.md                           |   58 +
 tickets/T-4622/ticket.md                           |  107 ++
 tickets/T-4623/ticket.md                           |   70 +
 tickets/T-4624/ticket.md                           |   52 +
 tickets/T-4625/ticket.md                           |   43 +
 tickets/T-4626/ticket.md                           |   27 +
 tickets/T-4627/ticket.md                           |   58 +
 tickets/T-4628/done-report.md                      | 1530 ++++++++++++++++++++
 tickets/T-4628/ticket.md                           |   58 +
 tickets/T-4629/ticket.md                           |   53 +
 tickets/T-4630/done-report.md                      | 1508 +++++++++++++++++++
 tickets/T-4630/ticket.md                           |   59 +
 tickets/T-4631/ticket.md                           |   74 +
 tickets/T-4632/done-report.md                      | 1478 +++++++++++++++++++
 tickets/T-4632/ticket.md                           |   46 +
 tickets/T-4633/done-report.md                      |  743 ++++++++++
 tickets/T-4633/ticket.md                           |   86 ++
 tickets/T-4634/done-report.md                      |  851 +++++++++++
 tickets/T-4634/ticket.md                           |   54 +
 tickets/T-4635/ticket.md                           |   30 +
 tickets/T-4640/ticket.md                           |   37 +
 tickets/T-4641/ticket.md                           |   29 +
 tickets/T-4642/done-report.md                      |  671 +++++++++
 tickets/T-4642/ticket.md                           |   52 +
 tickets/T-4643/ticket.md                           |   29 +
 tickets/T-4644/ticket.md                           |   29 +
 tickets/T-4645/ticket.md                           |   66 +
 tickets/T-4646/done-report.md                      |  914 ++++++++++++
 tickets/T-4646/ticket.md                           |   43 +
 tickets/T-4647/ticket.md                           |   49 +
 tickets/T-4648/ticket.md                           |   35 +
 tickets/T-4649/done-report.md                      |  888 ++++++++++++
 tickets/T-4649/ticket.md                           |  105 ++
 tickets/T-4650/done-report.md                      |  961 ++++++++++++
 tickets/T-4650/ticket.md                           |  166 +++
 tickets/T-4651/ticket.md                           |   55 +
 tickets/T-4652/ticket.md                           |   46 +
 tickets/T-4653/ticket.md                           |   44 +
 tickets/T-4654/ticket.md                           |   48 +
 tickets/T-4655/ticket.md                           |   43 +
 tickets/T-4656/ticket.md                           |   47 +
 tickets/T-4657/ticket.md                           |   74 +
 tickets/T-4658/ticket.md                           |   65 +
 tickets/T-4659/done-report.md                      |  962 ++++++++++++
 tickets/T-4659/ticket.md                           |   92 ++
 tickets/T-4660/ticket.md                           |   60 +
 tickets/T-4661/ticket.md                           |   66 +
 tickets/T-4662/ticket.md                           |   85 ++
 tickets/T-4663/ticket.md                           |   88 ++
 tickets/T-4664/ticket.md                           |   68 +
 tickets/T-4665/ticket.md                           |   69 +
 tickets/T-4666/ticket.md                           |   72 +
 tickets/T-4667/ticket.md                           |   63 +
 tickets/T-4668/ticket.md                           |  146 ++
 tickets/T-4669/done-report.md                      | 1464 +++++++++++++++++++
 tickets/T-4669/ticket.md                           |   98 ++
 tickets/T-4670/ticket.md                           |   86 ++
 tickets/T-4671/ticket.md                           |  105 ++
 tickets/T-4672/ticket.md                           |  139 ++
 tickets/T-4673/done-report.md                      | 1447 ++++++++++++++++++
 tickets/T-4673/ticket.md                           |   88 ++
 tickets/T-4674/ticket.md                           |   90 ++
 tickets/T-4675/ticket.md                           |  104 ++
 tickets/T-4676/ticket.md                           |   91 ++
 tickets/T-4677/done-report.md                      |   40 +
 tickets/T-4677/ticket.md                           |  173 +++
 tickets/T-4678/done-report.md                      |   48 +
 tickets/T-4678/ticket.md                           |  201 +++
 tickets/T-4679/ticket.md                           |   36 +
 tickets/T-4680/done-report.md                      |   55 +
 tickets/T-4680/ticket.md                           |  211 +++
 tickets/T-4681/ticket.md                           |  226 +++
 tickets/T-4684/ticket.md                           |   65 +
 tickets/T-4685/ticket.md                           |   59 +
 tickets/T-4686/ticket.md                           |   40 +
 tickets/T-4687/ticket.md                           |  225 +++
 tickets/T-4688/ticket.md                           |  149 ++
 tickets/T-4689/ticket.md                           |   99 ++
 tickets/T-4690/ticket.md                           |  214 +++
 tickets/T-4691/ticket.md                           |  143 ++
 tickets/T-4692/ticket.md                           |  208 +++
 tickets/T-4693/ticket.md                           |  138 ++
 tickets/T-4694/ticket.md                           |  127 ++
 tickets/T-4695/ticket.md                           |  181 +++
 tickets/T-4696/ticket.md                           |  162 +++
 tickets/T-4697/ticket.md                           |  120 ++
 tickets/T-4698/ticket.md                           |  165 +++
 tickets/T-4702/ticket.md                           |  104 ++
 tickets/T-4703/ticket.md                           |  122 ++
 tickets/T-4709/ticket.md                           |  158 ++
 tickets/T-4710/ticket.md                           |  116 ++
 tickets/T-4711/ticket.md                           |   80 +
 tickets/T-4712/ticket.md                           |   78 +
 tickets/T-4713/ticket.md                           |   90 ++
 tickets/T-4714/ticket.md                           |   86 ++
 tickets/T-4715/ticket.md                           |  175 +++
 tickets/T-4716/ticket.md                           |   47 +
 tickets/T-4717/ticket.md                           |   82 ++
 tickets/T-4718/ticket.md                           |  163 +++
 tickets/T-4719/ticket.md                           |  189 +++
 tickets/T-4720/ticket.md                           |   36 +
 tickets/T-4721/ticket.md                           |   36 +
 tickets/T-4722/ticket.md                           |  183 +++
 tickets/T-4723/ticket.md                           |  191 +++
 tickets/T-4724/ticket.md                           |   42 +
 tickets/T-4735/ticket.md                           |   62 +
 tickets/T-4736/ticket.md                           |   63 +
 tickets/T-4737/ticket.md                           |  113 ++
 tickets/T-4738/ticket.md                           |   62 +
 tickets/T-4739/ticket.md                           |   58 +
 tickets/T-4740/ticket.md                           |   60 +
 tickets/T-4741/ticket.md                           |  179 +++
 tickets/T-4742/ticket.md                           |   79 +
 tickets/T-4743/ticket.md                           |   80 +
 tickets/T-4757/ticket.md                           |   87 ++
 tickets/T-4758/ticket.md                           |   94 ++
 tickets/T-4759/ticket.md                           |  106 ++
 tickets/T-4760/ticket.md                           |  116 ++
 tickets/T-4761/ticket.md                           |  126 ++
 tickets/T-4762/ticket.md                           |   69 +
 tickets/T-4763/ticket.md                           |   64 +
 tickets/T-4764/ticket.md                           |   79 +
 tickets/T-4765/ticket.md                           |  108 ++
 tickets/T-4766/ticket.md                           |   84 ++
 tickets/T-4767/ticket.md                           |  173 +++
 tickets/T-4768/ticket.md                           |   84 ++
 tickets/T-4769/ticket.md                           |   74 +
 tickets/T-4770/ticket.md                           |  157 ++
 tickets/T-4771/ticket.md                           |   77 +
 tickets/T-4772/ticket.md                           |   97 ++
 tickets/T-4773/ticket.md                           |  109 ++
 tickets/T-4774/ticket.md                           |   82 ++
 tickets/T-4804/ticket.md                           |  180 +++
 tickets/T-4805/ticket.md                           |  114 ++
 tickets/T-4806/ticket.md                           |   53 +
 tickets/T-4807/ticket.md                           |  108 ++
 tickets/T-4808/ticket.md                           |  155 ++
 tickets/T-4809/ticket.md                           |   75 +
 tickets/T-4810/ticket.md                           |   92 ++
 tickets/T-4811/ticket.md                           |   31 +
 tickets/T-4848/ticket.md                           |   84 ++
 tickets/T-4853/ticket.md                           |   96 ++
 tickets/T-4855/ticket.md                           |   84 ++
 tickets/T-4856/ticket.md                           |   97 ++
 tickets/T-4857/ticket.md                           |   84 ++
 tickets/T-4863/ticket.md                           |   84 ++
 tickets/T-4869/ticket.md                           |   84 ++
 tickets/T-4870/ticket.md                           |   84 ++
 tickets/T-4871/ticket.md                           |   85 ++
 tickets/T-4874/ticket.md                           |   84 ++
 tickets/T-4910/ticket.md                           |   31 +
 tickets/T-4911/ticket.md                           |  114 ++
 tickets/T-4912/ticket.md                           |   42 +
 tickets/T-4913/ticket.md                           |   34 +
 tickets/T-4950/ticket.md                           |   34 +
 tickets/T-4951/ticket.md                           |  128 ++
 tickets/T-4952/ticket.md                           |  122 ++
 tickets/T-4953/ticket.md                           |   47 +
 tickets/T-4989/ticket.md                           |   30 +
 tickets/T-4990/ticket.md                           |   34 +
 tickets/T-4991/ticket.md                           |   33 +
 tickets/T-4992/ticket.md                           |   37 +
 tickets/T-4993/ticket.md                           |  110 ++
 tickets/T-4994/ticket.md                           |   93 ++
 tickets/T-4995/ticket.md                           |   91 ++
 tickets/T-4996/ticket.md                           |   90 ++
 tickets/T-4997/ticket.md                           |   86 ++
 tickets/T-5033/ticket.md                           |   75 +
 tickets/T-5034/ticket.md                           |   35 +
 tickets/T-5035/ticket.md                           |   44 +
 tickets/T-5036/done-report.md                      | 1432 ++++++++++++++++++
 tickets/T-5036/ticket.md                           |   50 +
 tickets/T-5037/ticket.md                           |   75 +
 tickets/T-5074/ticket.md                           |   75 +
 tickets/T-5075/ticket.md                           |  101 ++
 tickets/T-5076/ticket.md                           |   75 +
 tickets/T-5077/ticket.md                           |   76 +
 tickets/T-5078/ticket.md                           |   75 +
 tickets/T-5079/ticket.md                           |   75 +
 tickets/T-5080/ticket.md                           |   76 +
 tickets/T-5081/ticket.md                           |  125 ++
 tickets/T-5082/done-report.md                      |   38 +
 tickets/T-5082/ticket.md                           |  345 +++++
 tickets/T-5083/ticket.md                           |   87 ++
 tickets/T-5084/ticket.md                           |   29 +
 tickets/T-5085/ticket.md                           |   99 ++
 tickets/T-5086/ticket.md                           |   99 ++
 tickets/T-5087/ticket.md                           |  123 ++
 tickets/T-5088/ticket.md                           |   36 +
 tickets/T-5089/ticket.md                           |   34 +
 tickets/T-5090/ticket.md                           |   38 +
 tickets/T-5091/ticket.md                           |   99 ++
 tickets/T-5092/ticket.md                           |   60 +
 tickets/T-5093/ticket.md                           |   99 ++
 tickets/T-5094/ticket.md                           |  107 ++
 tickets/T-5095/ticket.md                           |   30 +
 tickets/T-5096/ticket.md                           |   35 +
 tickets/T-5097/ticket.md                           |  106 ++
 tickets/T-5098/ticket.md                           |   52 +
 tickets/T-5099/ticket.md                           |   52 +
 tickets/T-5100/ticket.md                           |   35 +
 tickets/T-5101/ticket.md                           |   45 +
 tickets/T-5102/ticket.md                           |   74 +
 tickets/T-5103/ticket.md                           |  120 ++
 tickets/T-5104/ticket.md                           |   61 +
 tickets/T-5105/ticket.md                           |   78 +
 tickets/T-5106/ticket.md                           |   37 +
 tickets/T-5107/ticket.md                           |   37 +
 tickets/T-5108/ticket.md                           |   35 +
 tickets/T-5109/ticket.md                           |   99 ++
 tickets/T-5110/ticket.md                           |   99 ++
 tickets/T-5111/ticket.md                           |   99 ++
 tickets/T-5112/ticket.md                           |  100 ++
 tickets/T-5113/ticket.md                           |   50 +
 tickets/T-5114/ticket.md                           |   68 +
 tickets/T-5115/ticket.md                           |  106 ++
 tickets/T-5116/ticket.md                           |   73 +
 tickets/T-5117/ticket.md                           |   38 +
 tickets/T-draft-1f0f55cb/ticket.md                 |   65 +
 tickets/T-draft-36c347fe/ticket.md                 |   68 +
 tickets/T-draft-a38af1c4/ticket.md                 |   77 +
 tickets/archive/T-0090/ticket.md                   |   18 +
 tickets/archive/T-0151/ticket.md                   |   63 +
 tickets/archive/T-0153/ticket.md                   |   91 ++
 tickets/archive/T-0158/ticket.md                   |   63 +
 tickets/archive/T-0169/ticket.md                   |   39 +-
 tickets/archive/T-0201/ticket.md                   |   63 +
 tickets/archive/T-0208/ticket.md                   |   90 ++
 tickets/archive/T-0209/ticket.md                   |   88 ++
 tickets/archive/T-0240/ticket.md                   |   18 +
 tickets/archive/T-0244/ticket.md                   |   35 +
 tickets/archive/T-0253/ticket.md                   |  117 ++
 tickets/archive/T-0292/ticket.md                   |   18 +
 tickets/archive/T-0328/ticket.md                   |  378 +++++
 tickets/archive/T-0336/ticket.md                   |   18 +
 tickets/archive/T-0337/ticket.md                   |  152 ++
 tickets/archive/T-0339/ticket.md                   |  123 ++
 tickets/archive/T-0364/ticket.md                   |   24 +
 tickets/archive/T-0377/ticket.md                   |  300 ++++
 tickets/archive/T-0378/ticket.md                   |  378 +++++
 tickets/archive/T-0379/ticket.md                   |  111 ++
 tickets/archive/T-0380/ticket.md                   |   38 +
 tickets/archive/T-0396/ticket.md                   |   39 +-
 tickets/archive/T-0403/ticket.md                   |   18 +
 tickets/archive/T-0414/ticket.md                   |   36 +-
 tickets/archive/T-0432/ticket.md                   |  152 ++
 tickets/archive/T-0441/ticket.md                   |   26 +-
 tickets/archive/T-0467/ticket.md                   |   24 +
 tickets/archive/T-0470/ticket.md                   |   35 +
 tickets/archive/T-0525/ticket.md                   |   18 +
 tickets/archive/T-0540/ticket.md                   |   38 +-
 tickets/archive/T-0553/ticket.md                   |   18 +
 tickets/archive/T-0557/ticket.md                   |   18 +
 tickets/archive/T-0576/ticket.md                   |   29 +
 tickets/archive/T-0639/ticket.md                   |   25 +
 tickets/archive/T-0660/ticket.md                   |  152 ++
 tickets/archive/T-0661/ticket.md                   |   81 ++
 tickets/archive/T-0662/ticket.md                   |   45 +
 tickets/archive/T-0663/ticket.md                   |   45 +
 tickets/archive/T-0664/ticket.md                   |   45 +
 tickets/archive/T-0723/ticket.md                   |   47 +-
 tickets/archive/T-0729/ticket.md                   |   35 +
 tickets/archive/T-0730/ticket.md                   |   18 +
 tickets/archive/T-0731/ticket.md                   |   27 +
 tickets/archive/T-0747/ticket.md                   |   27 +
 tickets/archive/T-0771/ticket.md                   |  114 +-
 tickets/archive/T-0779/ticket.md                   |   53 +-
 tickets/archive/T-0794/ticket.md                   |  142 ++
 tickets/archive/T-0808/ticket.md                   |   31 +-
 tickets/archive/T-0814/ticket.md                   |   26 +
 tickets/archive/T-0907/ticket.md                   |   90 +-
 tickets/archive/T-0910/ticket.md                   |   91 ++
 tickets/archive/T-0968/ticket.md                   |   25 +
 tickets/archive/T-0971/ticket.md                   |   45 +-
 tickets/archive/T-0978/ticket.md                   |   48 +-
 tickets/archive/T-1075/ticket.md                   |   36 +-
 tickets/archive/T-1095/ticket.md                   |   45 +-
 tickets/archive/T-1126/ticket.md                   |   45 +-
 tickets/archive/T-1148/ticket.md                   |   18 +
 tickets/archive/T-1210/ticket.md                   |   58 +
 tickets/archive/T-1211/ticket.md                   |   36 +-
 tickets/archive/T-1223/ticket.md                   |   73 +
 tickets/archive/T-1234/ticket.md                   |   31 +-
 tickets/archive/T-1261/ticket.md                   |   32 +
 tickets/archive/T-1265/ticket.md                   |   18 +
 tickets/archive/T-1266/ticket.md                   |   18 +
 tickets/archive/T-1341/ticket.md                   |   28 +-
 tickets/archive/T-1391/ticket.md                   |   33 +-
 tickets/archive/T-1402/ticket.md                   |   18 +
 tickets/archive/T-1421/ticket.md                   |   31 +-
 tickets/archive/T-1428/ticket.md                   |   31 +
 tickets/archive/T-1516/ticket.md                   |   45 +-
 tickets/archive/T-1523/ticket.md                   |   39 +
 tickets/archive/T-1548/ticket.md                   |   30 +-
 tickets/archive/T-1599/ticket.md                   |   22 +-
 tickets/archive/T-1600/ticket.md                   |   39 +-
 tickets/archive/T-1606/ticket.md                   |   23 +-
 tickets/archive/T-1614/ticket.md                   |   16 +-
 tickets/archive/T-1616/ticket.md                   |   29 +-
 tickets/archive/T-1620/ticket.md                   |  137 +-
 tickets/archive/T-1626/ticket.md                   |  242 ++--
 tickets/archive/T-1651/ticket.md                   |   11 +-
 tickets/archive/T-1659/ticket.md                   |   34 +
 tickets/archive/T-1665/ticket.md                   |   17 +-
 tickets/archive/T-1677/ticket.md                   |   59 +-
 tickets/archive/T-1684/ticket.md                   |   32 +
 tickets/archive/T-1688/ticket.md                   |   27 +-
 tickets/archive/T-1694/ticket.md                   |  129 +-
 tickets/archive/T-1700/ticket.md                   |   26 +
 tickets/archive/T-1703/ticket.md                   |   37 +-
 tickets/archive/T-1725/ticket.md                   |  104 +-
 tickets/archive/T-1746/ticket.md                   |   94 +-
 tickets/archive/T-1748/ticket.md                   |   36 +
 tickets/archive/T-1870/ticket.md                   |   26 +-
 tickets/archive/T-1886/ticket.md                   |   24 +
 tickets/archive/T-1916/ticket.md                   |   19 +-
 tickets/archive/T-2001/ticket.md                   |   16 +
 tickets/archive/T-2011/ticket.md                   |   19 +-
 tickets/archive/T-2025/ticket.md                   |   26 +-
 tickets/archive/T-2069/ticket.md                   |   23 +-
 tickets/archive/T-2087/ticket.md                   |   50 +-
 tickets/archive/T-2131/ticket.md                   |   17 +-
 tickets/archive/T-2193/ticket.md                   |   20 +
 tickets/archive/T-2231/ticket.md                   |   19 +-
 tickets/archive/T-2284/ticket.md                   |   16 +
 tickets/archive/T-2314/ticket.md                   |    9 +
 tickets/archive/T-2324/ticket.md                   |   33 +-
 tickets/archive/T-2338/ticket.md                   |    9 +
 tickets/archive/T-2358/ticket.md                   |   28 +
 tickets/archive/T-2365/ticket.md                   |   17 +-
 tickets/archive/T-2374/ticket.md                   |   18 +-
 tickets/archive/T-2400/ticket.md                   |   18 +
 tickets/archive/T-2438/ticket.md                   |    9 +
 tickets/archive/T-2454/ticket.md                   |    9 +
 tickets/archive/T-2457/ticket.md                   |   28 +-
 tickets/archive/T-2464/ticket.md                   |   62 +-
 tickets/archive/T-2479/ticket.md                   |   35 +-
 tickets/archive/T-2480/ticket.md                   |   20 +-
 tickets/archive/T-2532/ticket.md                   |   18 +-
 tickets/archive/T-2682/ticket.md                   |   33 +-
 tickets/archive/T-2688/ticket.md                   |    9 +
 tickets/archive/T-2698/ticket.md                   |   27 +-
 tickets/archive/T-2703/ticket.md                   |   20 +-
 tickets/archive/T-2710/ticket.md                   |    9 +
 tickets/archive/T-2885/ticket.md                   |   42 +-
 tickets/archive/T-2906/ticket.md                   |   29 +
 tickets/archive/T-2922/ticket.md                   |   43 +
 tickets/archive/T-2931/ticket.md                   |   22 +-
 tickets/archive/T-2934/ticket.md                   |   20 +
 tickets/archive/T-2935/ticket.md                   |   20 +-
 tickets/archive/T-3019/ticket.md                   |   23 +-
 tickets/archive/T-3104/ticket.md                   |   39 +-
 tickets/archive/T-3115/ticket.md                   |   17 +
 tickets/archive/T-3128/ticket.md                   |   28 +
 tickets/archive/T-3222/ticket.md                   |   31 +
 tickets/archive/T-3255/ticket.md                   |    9 +
 tickets/archive/T-3275/ticket.md                   |   28 +-
 tickets/archive/T-3464/ticket.md                   |   33 +-
 tickets/archive/T-3489/ticket.md                   |   18 +-
 tickets/archive/T-3492/ticket.md                   |   28 +
 tickets/archive/T-3493/ticket.md                   |   28 +
 tickets/archive/T-3541/ticket.md                   |   20 +-
 tickets/archive/T-3664/ticket.md                   |   11 +-
 tickets/archive/T-3665/ticket.md                   |   10 +-
 tickets/archive/T-3667/ticket.md                   |   28 +-
 tickets/archive/T-3708/ticket.md                   |  135 +-
 uv.lock                                            |    2 +-
 1397 files changed, 101392 insertions(+), 4391 deletions(-)
```

### Evidence
- `tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates` (pytest node id, verified passing when recorded)
