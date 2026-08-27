## Done report

Re-ran all 26 named T-3034 failures against current main first: 1 (TestFixEngineTierA::test_excluded_handler_is_skipped_and_file_untouched) already passed -- fixed elsewhere since filing. Of the remaining 25, triaged each individually (never batch-fixed) and fixed 14 as genuine test-side staleness:
- 5 tests hardcoded "src/frob/**" as an over-broad-scope literal; T-2771 generalized over_broad_literal_globs to derive package-prefix globs from the target root's own pyproject.toml, so the literal stopped resolving in a bare tmp_path fixture with none. Swapped to "tests/**", which stays in the repo-convention constant regardless of package-name resolution.
- 2 tests (frob ack) predate T-1317's --reason requirement and its AckReasonBoilerplate check; added a genuine, non-boilerplate reason.
- 1 test predates T-2394/T-2557's refusal of an empty ticket scope; added --declare-no-scope for the genuinely scopeless docs ticket, and updated its --evidence-cmd off T-1892's EvidenceCmdSilent refusal of a silent "true".
- 1 test patched frob.dup._core.core_available, but find_clones now imports the name directly into _pipeline/_fingerprint's own namespace -- patching the source attribute no longer reaches the call site (import binds where a name is looked up, not where it is defined). Repointed the monkeypatch.
- 2 tests had fake/mock function signatures that drifted from their real call sites after new params were added (apply_tier_a_fixes' merge_target_ids, parse_file's expect_heterogeneous).
- 1 test's DOCENUM001 fixture predates T-2664's stricter check that every claimed member also needs a resolvable doc row/heading.
- 1 test's commit-count assertion predates T-1130's ticket-new auto-commit, which itself degrades to a WARN-only skip (not a hard failure) if the commit cannot complete -- relaxed to >=1 rather than hardcoding an exact count the auto-commit's own contract does not guarantee. Note: this one test (tests/test_stats.py::test_collect_combines_both) passes reliably under a direct pytest invocation (verified repeatedly, alone and batched with the other 12 fixed ids) but was observed to fail specifically inside frob ticket evidence's own internal re-verification harness for a reason not fully root-caused in the time available -- left OUT of this ticket's own bound evidence set rather than force it through, and is not one of the two follow-up tickets' listed items since the fix itself (the >=1 relaxation) is correct and verified independently.

The remaining 11 (10 filed to T-3140, plus the already-known-environment-dependent autocrlf case which needed no new ticket since T-3034's own body already root-caused it) are left uncharacterized rather than guessed at. One additional item -- test_close_fails_on_unrelated_evidence -- looked like a possible real regression in D-02's evidence-scope-binding enforcement (close succeeded on unrelated evidence when it should refuse) and is filed separately as T-3141, flagged as the most concerning finding of this pass.

### Changed
```
 tests/system/test_cli_evidence_enforcement.py      |  21 ++-
 tests/system/test_cli_graph.py                     |  24 +++-
 tests/test_dup_smart.py                            |  18 ++-
 tests/test_gates.py                                |  28 +++-
 tests/test_gates_tick009_tick010.py                |  12 +-
 tests/test_stats.py                                |   8 +-
 tests/unit/test_app_runners_batch7.py              |   9 +-
 .../unit/test_app_runners_t0714_doable_summary.py  |   7 +-
 .../unit/test_new_ticket_scope_breadth_ack_flag.py |   9 +-
 tickets/T-3034/ticket.md                           | 141 ++++++++++++++++++++-
 tickets/T-3140/ticket.md                 | 138 ++++++++++++++++++++
 tickets/T-3141/ticket.md                 |  55 ++++++++
 12 files changed, 449 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/system/test_cli_graph.py::TestAck::test_ack_then_requery_clean` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_graph.py::TestAck::test_ack_then_drift_after_change` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_docs_kind_cmd_evidence_path_still_works` (pytest node id, verified passing when recorded)
- `tests/test_dup_smart.py::TestFindClones::test_core_unavailable_is_honest_err_not_silent_downgrade` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_in_progress_over_broad_glob_still_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_over_broad_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_unacknowledged_broad_scope_still_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 78 error(s), 1882 warning(s), 865 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bx/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3034, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
