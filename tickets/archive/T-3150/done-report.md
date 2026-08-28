## Done report

Changed:
- scripts/fleet_status.py::worktrees_touching_ticket -- added a third
  correlation tier between the existing start-transition fast path and
  the strict dual-correlation fallback.
- tests/unit/test_coordinator_scripts.py -- two new tests (must-fire,
  must-stay-quiet) for the new tier.

Root cause: `_worktree_matches_ticket_by_dual_correlation` requires a
SINGLE commit in the worktree's own `main..HEAD` history to touch BOTH
`tickets/<id>/` and a declared-scope file. When a ticket is created on
`main` before the worktree branches (the ordinary `frob ticket new` then
`work` sequence), the ticket-dir-touching commit is in the shared base,
never in `main..HEAD` -- so this check can never match, regardless of how
much real scope-touching work the worktree does. `_worktree_started_
ticket` (the structural start-transition-commit signal, T-2747) does not
help either when that marker commit is absent from `main..HEAD` for any
reason (this ticket's own repro fixture, and potentially a squashed/
rebased history).

Fix: restored `_worktree_ticket_id` (T-2599's directory-naming-
convention resolver -- already implemented and tested, but "not wired to
any production call site" since T-2755 per its own docstring) as a
narrow third tier: when a worktree's directory name is LITERALLY `t-<id>`
for the SAME `ticket_id` being asked about, fall back to the weaker
scope-only check (same one the start-transition fast path already uses)
instead of the strict dual correlation. Exact-match only -- an ad-hoc or
series-shared worktree name never matches, so this cannot resurrect the
T-2114/T-2181 false positive (measured branches with names like
`t-2107`, `t2049-series` that never literally equal `t-<queried-id>`).

Test-first (BUG002): confirmed the repro FAILS at the parent commit via
`frob ticket evidence --designate-repro` (recorded below) before the fix
landed in this same worktree; re-ran green after.

Must-stay-quiet: added
`test_ticket_named_worktree_for_a_different_ticket_id_not_matched` --
a worktree named `t-2199` queried for a DIFFERENT ticket id (`T-2200`)
does not match via the new tier, proving it is gated by exact id
equality, not by "looks like a ticket-named worktree."

Filed: none.

Gates: `frob check --ticket T-3150` -- 0 errors in this ticket's own
scope (tests/unit/test_coordinator_scripts.py). Full local suite run:
`pytest tests/unit/test_coordinator_scripts.py -q` -- 235 passed, 0
failed (full module, not just the touched tests -- confirms no
regression elsewhere in the file).

### Changed
```
 tickets/T-3150/done-report.md | 65 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3150/ticket.md      |  8 ++++--
 tickets/T-3153/ticket.md      |  5 ++++
 3 files changed, 76 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ticket_named_worktree_with_no_start_marker_matches_via_name_fallback` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ticket_named_worktree_for_a_different_ticket_id_not_matched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 121 error(s), 863 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3150, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
