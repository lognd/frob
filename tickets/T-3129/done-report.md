## Done report

T-3129: added frob.app._version_guard.binary_fingerprint_warning, a git-HEAD-sha
content-identity check distinct from the two pre-existing version-string checks
(stale_install_warning/stale_binary_warning) -- neither can detect a stale global
binary whose declared version was never bumped past its last release, which is
exactly what happened: bare `frob` and `uv run frob` both reported the same
version string while exposing different CLI surfaces. Wired into
_print_startup_warnings alongside the existing two checks (scope expanded onto
src/frob/__main__.py and docs/modules/app.md with a recorded reason -- required
by this ticket's own acceptance criteria that the warning actually fire on
invocation, not a separable concern).

Evidence: tests/unit/test_version_guard.py (6 tests, real git repos in tmp_path,
not mocked git calls) -- must-stay-quiet covers editable in-tree run, matching-sha
sibling checkout, non-frob repo, and no-spec; must-fire covers mismatched sha and
unresolvable running sha (fail-safe-to-stale). frob test --base main: 8 outcomes,
python exit=0.

Blast radius measured beyond the two verbs the ticket named: bare `frob --help`
vs `uv run frob --help` also differ on top-level verbs `refactor`, `narrative`,
`status` and flag `-v/--verbose` -- entirely absent from the global binary,
version string identical (`frob 0.530.0` both). Recorded in docs/modules/app.md
and this Done report; not separately ticketed since it is evidence FOR this
ticket's premise, not new work.

Filed: none.

Gates: frob check --ticket T-3129 --only gates-fast/gates-native/gates-security/
lint/static all run; gate:SCOPE 0 errors; the diff introduced two gate:DOC006
findings (a symbol-pointer and a prose-backtick false positive), both fixed.
Every remaining error in every gate family was verified pre-existing and
unrelated to this ticket's files (grep against each stage's saved output for
_version_guard/__main__/app.md hits). Not closable to a repo-wide zero from
this ticket's scope -- confirmed via --ticket's own NOTE that non-SCOPE/PREWORK
counts are repo-wide, not diff-scoped.

### Changed
```
 tickets/T-3129/done-report.md | 50 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3129/ticket.md      | 38 ++++++++++++++++++++++++++++++--
 2 files changed, 86 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_version_guard.py::test_non_frob_repo_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_version_guard.py::test_editable_in_tree_run_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_version_guard.py::test_matching_sha_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_version_guard.py::test_mismatched_sha_warns_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_version_guard.py::test_unresolvable_running_sha_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_version_guard.py::test_no_frob_spec_is_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 121 error(s), 807 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3129, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
