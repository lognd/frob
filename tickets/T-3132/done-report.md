## Done report

Root cause: `_assert_touched_files_lint_clean_pre_land` (T-3061) refused
the land on ANY ruff violation in a touched file, with no comparison to
the file's own content at the ticket's merge-base -- identical shape to
the pre-T-3116 `ty` gate.

Fix: ported T-3116's diff-attribution mechanism -- a second `ruff` pass
against the same touched files at merge-base, in a detached snapshot
worktree (`_ruff_baseline_diagnostic_identities`), compared as a
multiset of `(file, code, message)` identity (`_ruff_diagnostic_identity`
/ `_ruff_new_violations`), excluding line/col. One divergence from the
`ty` version, load-bearing not cosmetic: ruff's JSON `filename` is
ABSOLUTE (resolved against the spawning cwd), unlike ty's, so identity
is re-derived via `os.path.relpath(diag.file, base)` rather than reusing
the caller's `file` argument directly -- confirmed by direct measurement
against a scratch fixture.

Measured effect: searched the ~2117 `frob:waive` directives and ~6336
`# noqa` suppressions for a reason referencing this gate's pressure
(T-3061, "pre-land", "touched file lint", or similar) -- zero real
hits (`frob:waive` targets frob's own gate rule ids, never a raw ruff
code, so it cannot be the escape hatch for this gate at all; sampled
`noqa` hits matching a loose land/refus/pre-existing grep were all
unrelated E501/E402 boilerplate). Same negative result as T-3116's own
ty-ignore measurement: the "suppression factory" hypothesis is not
confirmed for this gate either.

Fixtures: tests/test_ticket_land_lint_diff_attribution.py -- must-fire
(test_genuinely_new_violation_still_refuses,
test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses)
and must-stay-quiet
(test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse),
plus identity-unit and unmeasurable-baseline-fallback coverage.

Gates: `ruff check`/`ty check` clean on
src/frob/app/ticket_runner/_land_cmd.py; `frob ticket land` T-3132's own
pre-land lint gate passed clean on this diff.

### Changed
```
 docs/modules/tickets-landing.md                 |  61 +++++-
 src/frob/app/ticket_runner/_land_cmd.py         | 166 +++++++++++++++-
 tests/test_ticket_land_lint_diff_attribution.py | 240 ++++++++++++++++++++++++
 tickets/T-3132/ticket.md                        |   9 +-
 4 files changed, 459 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_ticket_land_lint_diff_attribution.py::TestRuffDiagnosticIdentity::test_ignores_line_and_col` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestRuffDiagnosticIdentity::test_relative_to_base_not_absolute` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_genuinely_new_violation_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_baseline_unmeasurable_falls_back_to_file_scoped_refusal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 119 error(s), 843 warning(s), 910 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3132, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
