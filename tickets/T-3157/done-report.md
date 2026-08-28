## Done report

Added tests/system/test_fleet_status_ground_truth.py: one test class per
claim fleet_status.py makes about the host it reports on (checks running,
land-lock holder-vs-waiter, worktree lease liveness, orphaned forkservers),
each with a must-fire and a must-stay-quiet fixture, wired as this ticket's
evidence (11 tests recorded via `frob ticket evidence`).

Acceptance denominator check (all 4 defects, verified by hand against each
one's own parent commit):

- (a) token match (`_is_live_check_cmdline`): at ef9d537c3 (parent of
  T-3093's land commit 11c99626b) the attribute does not exist at all --
  the must-fire/must-stay-quiet tests all raise AttributeError there.
  FAILS at parent, PASSES at HEAD.
- (b) land-lock true-holder-vs-waiter (`_true_flock_holder_pid`): same
  parent commit (T-3093 fixed both (a) and (b) in one land) -- the
  attribute does not exist. FAILS at parent, PASSES at HEAD.
- (c) worktree-leak false positive: T-3128 itself (dac790e6e) landed with
  NO code diff to scripts/fleet_status.py -- diffed 832a335df^ against
  HEAD, byte-identical. Its own designated repro test already passed at
  the parent commit, so the measured incident was environmental/race, not
  a reproducible code defect. Substituted the SAME claim's actual
  code-level regression in this file (T-2747, commit bf9c7c884): at
  29316f480 (bf9c7c884^) the must-fire fixture
  (test_must_fire_worktree_whose_start_transition_already_landed) FAILS
  (assert [] == ['waive-liveness']). PASSES at HEAD. This substitution is
  documented explicitly in the module and class docstrings so the gap
  between the claimed denominator and what is actually falsifiable stays
  visible.
- (d) orphan age floor (_ORPHAN_AGE_FLOOR_S / orphaned_forkserver_count):
  at 4da2a85c2 (parent of T-3139's land 6f04de4c8) the must-stay-quiet
  fixture reports 1 orphan instead of 0, and the cross-check test raises
  AttributeError. FAILS at parent, PASSES at HEAD.

All 11 tests pass at HEAD. `uv run frob test --base main` selects and runs
this file's 16 touched tests, exit=0. `uv run frob check --ticket T-3157
--json`, filtered on this file's path, reports zero diagnostics -- earlier
DUP001 hits against fixture-reuse helpers were a stale-check artifact
against the untracked file; `git add` plus re-running cleared them. Reuse
of tests/unit/test_coordinator_scripts.py's existing fixture helpers
(_run_git, _init_bare_repo, _write_proc_locks,
TestOrphanedForkserverCount's writers) is via a qualified module reference
(tests.unit.test_coordinator_scripts as _tcs), not a second copy, per NO
DUPLICATION.

Scope was narrowed off scripts/fleet_status.py at ticket-start time (T-3152
holds a live write lease on it); this ticket only ever needed read access
to it from the test file, which the narrowed scope still allows. No
out-of-scope work found; nothing filed.

Repo-wide ruff-format/ty/frob-cycle/claude-config-drift failures in the
full `frob check` run are pre-existing baseline noise across dozens of
unrelated files, not attributable to this change (confirmed by JSON
filtering on file path).

### Changed
```
 tickets/T-3157/ticket.md | 12 ++++++++++++
 1 file changed, 12 insertions(+)
```

### Evidence
- `tests/system/test_fleet_status_ground_truth.py::TestChecksRunningClaim::test_must_fire_on_python_dash_m_frob_check` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestChecksRunningClaim::test_must_fire_on_venv_executable_path_form` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestChecksRunningClaim::test_must_stay_quiet_on_frob_as_a_substring` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestChecksRunningClaim::test_must_stay_quiet_on_frob_without_check_subcommand` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_fire_the_true_holder_among_waiters` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_stay_quiet_when_only_waiters_hold_the_fd_open` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestOrphanedForkserverAgeFloorClaim::test_must_fire_on_old_forkserver_with_no_check_ancestor` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestOrphanedForkserverAgeFloorClaim::test_must_stay_quiet_on_young_forkserver_with_no_check_ancestor` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestOrphanedForkserverAgeFloorClaim::test_age_floor_matches_reap_orphaned_forkservers_default` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestWorktreeLeaseLeakClaim::test_must_fire_worktree_whose_start_transition_already_landed` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestWorktreeLeaseLeakClaim::test_must_stay_quiet_abandoned_ticket_with_no_worktree_at_all` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 121 error(s), 694 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3157, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
