## Done report

Root cause: DISTINCT from T-3123 (in-process leak BETWEEN tests in the
same pytest worker). This is `FROB_WORKTREE`/`FROB_AGENT` present in the
pytest worker's own `os.environ` from OUTSIDE the test session entirely
-- e.g. inherited via `frob ticket evidence`'s individual-reverify
subprocess spawn when the recording agent is itself working inside a
leased worktree (`run_selected`/`_run_one_runner`'s `run_argv`-based
spawn, used whenever `frob.toml` declares a `[[test.runner]]`, does not
strip these two vars from the child's environment the way the fully-
audited no-runner-declared `_run_pytest_directly` fallback already does,
T-0884). T-3123's own fixture (`_isolate_worktree_lease_env_before_test`)
only snapshots the value present at its OWN setup and restores exactly
that afterward -- it never clears the var during a test body, so a value
already present when the very first test's setup runs survives untouched
through every test the fixture wraps, restore or not.

Confirmed T-3123 does NOT already cover this path: read its landed
commit (`ef95d2599`, `tests/conftest.py`'s diff) directly -- the fixture
is restore-only, never a `pop` at setup. Wrote a repro
(`tests/test_worktree_lease_env_ambient.py`) that sets `FROB_WORKTREE`
via a MODULE-scoped autouse fixture (writes `os.environ` directly, not
`monkeypatch`, so it is present before `tests/conftest.py`'s function-
scoped fixture ever runs for this module's tests -- a plain
`monkeypatch.setenv` inside a test body cannot reproduce this, since
every applicable fixture's setup, including the conftest one, has
already completed by the time a test body runs) and confirmed it FAILED
at the parent commit (`Err(TicketError.WorktreeLeaseViolation)` on a
`new_ticket` call against a completely unrelated `tmp_path` repo).

Fix: `tests/conftest.py`'s `_isolate_worktree_lease_env_before_test` now
pops `FROB_WORKTREE`/`FROB_AGENT` at setup (in addition to its existing
snapshot/restore), so any test whose own body needs the guard to fire
opts in itself via `monkeypatch.setenv` after the pop, same idiom
`tests/test_gates.py::test_write_coverage_lock_refuses_under_lease_
violation` already uses. `PYTEST_XDIST_AUTO_NUM_WORKERS` is deliberately
left snapshot/restore-only (not popped) -- an ambient value there is
playbook section 1e's own intentional fleet-aware xdist bound, not a
correctness bug.

Verified: the new repro test now passes; `TestWorktreeLeaseEnvIsolation`
(T-3123's own 4 tests, `tests/test_ticket_land.py`) still pass unchanged
under `-p no:xdist`; the existing TICK006 fixture family (29 tests,
`tests/test_gates.py`) still passes; a direct repro of the ticket's own
measured incident --
`FROB_WORKTREE=/tmp/some-unrelated-real-dir pytest tests/test_gates.py::TestFixEngineTierA::test_tick006_refiles_and_rewrites_citation`
-- now passes (previously this exact invocation is how the failure was
originally measured); the opt-in guard-exercise test still fires
correctly (must-stay-quiet-in-reverse).

Scope note: widened from the ticket's declared `tests/conftest.py` alone
to also include the new `tests/test_worktree_lease_env_ambient.py`
(`frob ticket scope --add`, reason recorded on the ticket) -- `conftest.py`
itself is not pytest-collected (`python_files = test_*.py`), so a
repro/acceptance test proving the fixture's behavior cannot live there;
T-3123, this ticket's own precedent, declared both its fixture file and
a real test file in scope for the identical reason.

Gates: `ruff check`/`ty check` clean on both changed files.

### Changed
```
 tests/conftest.py                        |  59 ++++++++++---
 tests/test_worktree_lease_env_ambient.py | 142 +++++++++++++++++++++++++++++++
 tickets/T-3145/ticket.md                 |  28 +++++-
 3 files changed, 218 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_new_ticket_against_unrelated_repo_is_unaffected_by_an_ambient_frob_worktree` (pytest node id, verified passing when recorded)
- `tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_opt_in_worktree_lease_guard_still_fires_when_deliberately_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 120 error(s), 687 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3145, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
