## Done report

MEASURED before fixing: `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked`
(a pre-existing REAL-git-worktree fixture from T-2665, unchanged) was FAILING on main HEAD --
a real `git worktree add` with an unlanded commit touching the ticket's own scope, no lease
file, reported `leaked=True` when it should not have. This is the exact shape T-3128 measured
against T-3122 (worktree exists, is registered in `git worktree list`, has committed work, but
`fleet_status.py` reported it LEAK).

DISCRIMINATOR: `worktrees_touching_ticket`'s dual-path dispatch --
  1. If the worktree's own history carries `ticket_id`'s canonical start-transition commit
     (`chore(tickets): record <id> start transition`), a weaker scope-only match applies
     (T-2747).
  2. Otherwise, a strict dual-condition match requires ONE SINGLE commit to touch BOTH
     `tickets/<id>/` and a declared-scope file (T-2179/T-2181, to rule out a worktree that
     started a DIFFERENT ticket and merely shares scope files by coincidence).
A worktree whose start-transition commit for `ticket_id` has already landed onto `main`
through a sibling ticket's squash (dropping out of `main..HEAD`), or one created without going
through the standard `frob ticket start`/`work` path, satisfies NEITHER condition even though
it is a completely legitimate, currently-in-use worktree for that ticket: its start-transition
commit and its real work commits are normally two SEPARATE commits to begin with, so path 2's
same-commit requirement can never be satisfied by ordinary workflow shape, and path 1 requires
the start-transition commit to still be present in `main..HEAD`.

FIX: added a third branch -- when the worktree names NO start-transition commit for ANY ticket
at all (`_worktree_started_ticket_ids(path) == []`), the T-2181 collision risk the strict
dual-condition check exists to prevent (a worktree that structurally started a DIFFERENT
ticket) cannot occur, so scope-only matching is safe there too. Every worktree that started at
least one OTHER ticket still gets the original, stricter check -- T-2114/T-2181 are unaffected
(verified: `TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated`
still passes unchanged).

T-2992 VERDICT: REAL leak, not a false positive. `tickets/T-2992/ticket.md` declares
`no_scope_declared: true` (pure investigation ticket, no scope globs at all) and has no
`.git/frob-leases/T-2992.json` and no registered `git worktree`. `in_progress_ticket_scope_
leases`'s scope-correlated fallback (`worktrees_touching_ticket`) always returns `[]` for empty
scope_globs by design (T-2179's own explicit guard: "no known scope to check against" must
never read as "implementation confirmed") -- there is structurally no way to resolve a worktree
for this ticket, matching, and this is correct: no worktree exists for T-2992 anywhere.

CLEANUP CONSUMER: `in_progress_ticket_scope_leases`'s `leaked` field is consumed ONLY by
`_leases_report` (a human-facing print line, `LEASES N (... leaked ...)`) -- grepped the whole
`scripts/` and `src/frob/` trees; no sweep/prune/`--finish` verb reads this function's output.
The blast radius as measured is "an operator sees a wrong count and may act on it by hand" (the
exact thing that happened before this ticket was filed), not an automated deletion today -- but
the ticket's own body is right that this is still the correct signal any future automated sweep
would reach for first, so the false positive needed fixing regardless.

Evidence: the pre-existing failing repro now passes (BUG002 FAILED_AT_PARENT / PASSES_AT_FIX);
full `tests/unit/test_coordinator_scripts.py` (238 tests) green; `ruff check`/`ruff format`
clean on the touched files; `frob check --ticket T-3128` gate:SCOPE clean (0 errors).
No new tickets filed for this half.

### Changed
```
 scripts/fleet_status.py                | 119 ++++++++++++--
 tests/unit/test_coordinator_scripts.py | 284 +++++++++++++++++++++++++++++++--
 tickets/T-3128/ticket.md               |   7 +-
 tickets/T-3139/ticket.md               |   9 +-
 4 files changed, 386 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_no_worktree_and_no_lease_is_still_leaked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 124 error(s), 924 warning(s), 872 waived
- error-findings: AFFECT001@scripts/fleet_status.py, ARCH001@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@scripts/fleet_status.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV005@scripts/fleet_status.py, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3128, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
