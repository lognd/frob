## Done report

MEASURED against the real T-3086 split's own gates/_models.py content
(a scratch repo built from the parent commit's real file text, not a
synthetic fixture): all ~25 of the non-gates import sites left
unrepointed used the moved names in ordinary expression position (a
call, an attribute access), never annotation-only -- the annotation
hypothesis this ticket set out to check was FALSIFIED. The real cause:
`_handle_from_import`'s "co-imported name present -> skip the whole
rewrite" guard (added by T-3105 to stop a genuinely untouched name being
dragged to the destination) fires identically whether that co-imported
name is a real bystander OR another symbol being moved in the SAME split
batch -- `scan_references` runs once per symbol with no visibility into
its own siblings, so `from gates._models import Severity, Violation`
(both moving together) was skipped exactly like a real mixed line would
be.

Fix: `scan_references`/`build_plan` now take an `also_moving` set naming
every sibling symbol moving to the same destination in this operation;
`_split.py`'s own chunk loop passes each symbol's chunk-mates. A shared
import line where every non-current name is in that set is folded into
ONE rewrite (`from dest import A, B`) instead of being skipped; a line
mixing a moved name with a genuinely untouched one still blocks
exactly as before (T-3105 preserved, regression-tested).

Verified against real production content: built a scratch repo from the
literal parent-commit text of gates/_models.py, dup/_rules.py,
fuzz/_rules.py, perf/_advisories.py, policy/__init__.py,
vet/_ecosystem.py, vet/_scan.py and ran scan_references with the fix --
all 6 non-gates importers that were silently left pointed at
gates._models now produce a rewrite op repointing them at
frob.findings, confirming the fix closes the real measured gap without
touching application code in this ticket (that repoint is a separate,
much larger migration; not attempted here).

Filed T-3153 (residue, not in this ticket's scope): the new
regression corpus fixture surfaced a genuinely pre-existing,
unrelated bug -- `tests/test_refactor_corpus.py`'s own `new_ticket()`
fixture call trips `frob.tickets._worktree_guard`'s mutation refusal
whenever the test runs individually inside an agent's leased worktree
(reproduced identically against main's unmodified copy of the same
test), which is exactly the context `frob ticket evidence`'s own
individual-rerun path uses -- so the corpus test could not itself be
bound as evidence here, only the pre-existing scan_references/
build_plan/run_split coverage in tests/test_refactor.py plus the new
also_moving-shaped tests there.

### Changed
```
 docs/commands/refactor.md          |  14 +++-
 src/frob/refactor/_scan.py         | 110 ++++++++++++++++++++++++-------
 src/frob/refactor/_split.py        |  17 ++++-
 src/frob/refactor/_transaction.py  |  17 +++--
 tests/test_refactor.py             |  91 +++++++++++++++++++++++---
 tests/test_refactor_corpus.py      |  51 +++++++++++++++
 tickets/T-3143/ticket.md           | 131 ++++++++++++++++++++++++++++++++++++-
 tickets/T-3153/ticket.md |  49 ++++++++++++++
 8 files changed, 438 insertions(+), 42 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_also_moving_sibling_on_same_line_is_folded_into_rewrite` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_also_moving_sibling_plus_genuinely_untouched_name_still_blocks` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_mixed_moved_and_untouched_names_leaves_import_alone` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 120 error(s), 871 warning(s), 879 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-cc/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3143, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
