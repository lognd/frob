## Done report

Root cause: frob.tickets._worktree_guard.apply_agent_env (T-3094) mutates
os.environ directly (os.environ.update) with no restore. Correct for its
real production callers (each a short-lived CLI process), but land()'s
post-merge evidence re-verification path (_verify.py:2163) calls it against
the worktree tmp_path fixture, leaking FROB_WORKTREE into the long-lived
pytest worker for every later test.

Measured (series BZ, 2026-08-27, this worktree):
- Before fix: uv run pytest -p no:xdist tests/test_ticket_land.py ->
  154 of 330 failed, all TicketError.WorktreeLeaseViolation.
- After fix: same command -> 5 of 330 failed, ZERO WorktreeLeaseViolation.
- True floor: 5 real, pre-existing failures, unrelated to the leak,
  reproduced both in the full-file run and standalone by node id. Filed
  separately as T-3144 (out of this ticket's scope).
- Confirmed via a diagnostic pytest_runtest_setup hook: every one of the
  330 tests now sees FROB_WORKTREE=None at its own setup.

Filed: T-3144 (5 real pre-existing failures in
tests/test_ticket_land.py, unmasked by this fix).

### Changed
```
 tests/conftest.py                  | 51 ++++++++++++++++++++
 tests/test_ticket_land.py          | 96 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3123/done-report.md      | 41 ++++++++++++++++
 tickets/T-3123/ticket.md           | 19 ++++++--
 tickets/T-3144/ticket.md | 47 +++++++++++++++++++
 5 files changed, 251 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_a_leaves_frob_worktree_set_like_apply_agent_env_does` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_b_does_not_see_a_leaked_frob_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_apply_agent_env_leak_is_contained_to_its_own_test` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_must_stay_quiet_after_apply_agent_env_leak` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 80 error(s), 902 warning(s), 871 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bz/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3123, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@tests/test_ticket_land.py
