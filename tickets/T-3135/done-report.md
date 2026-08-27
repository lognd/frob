## Done report

Implemented the persistent warm sweep stage T-3127's failure log identified
as the only shape that could work.

WHAT: `_ensure_warm_sweep_stage`/`_reset_warm_sweep_stage`/
`_teardown_warm_sweep_stage`/`_squash_into_warm_stage` (src/frob/tickets/
_land.py) give the T-1514 pre-commit sweep a `git worktree` at
`<root>/.frob/warm-sweep-stage` that PERSISTS across lands (created once,
hard-reset + `git clean -fdx -e .venv -e .frob` on reuse) instead of a
fresh disposable one cut per land. `_squash_apply_on_disposable_stage`'s
carve-out (T-3121: a supplied `pre_commit_sweep` used to keep the sweep
in-root unconditionally, because a bare disposable stage cannot measure
anything) now tries the warm stage first -- squash-composing into it via
the same `_squash_into_worktree` `_land_compose.py` already uses for the
disposable path -- and only falls back to the old in-root behavior if the
warm stage cannot be prepared or squash-composed cleanly.

WHY THIS ADDRESSES T-3127's TWO STRUCTURAL BLOCKERS (both measured, not
reasoned, in that ticket's own failure log): (1) the chunk planner's
timing model has no headroom in a tree it has never measured -- a warm
stage that survives across lands accumulates real timing data the same
way `root` already does, instead of starting cold every time; (2) native
staleness from a symlinked venv built against a different tree -- the
warm stage owns its own REAL venv/natives (never symlinked from root), so
`frob check`'s own `_maybe_autorebuild_natives`/`stale_natives` self-heals
it exactly as it does for `root`, structurally rather than by provisioning
trick.

ACCEPTANCE (from T-3135's own text): "a land engages the disposable stage
AND the T-1514 sweep returns a MEASURED result about the staged
changeset" -- proven by `test_pre_commit_sweep_engages_the_warm_stage_not_root`
(must-fire: the sweep receives the warm stage path, not root, holding the
real staged changeset) and `test_warm_stage_reused_across_lands` (must-fire:
a second land reuses the EXACT same stage path -- the whole point of
"persistent" over "disposable"). `test_warm_stage_unavailable_falls_back_to_root`
is the must-stay-quiet counterpart: when the stage cannot be prepared, the
sweep degrades to the pre-T-3135 in-root path, never silently skipped.
The pre-existing `test_root_never_goes_dirty_during_the_squash_apply` /
`test_worktree_setup_failure_refuses_without_touching_root` (T-3121) still
pass unmodified.

DEFERRED TO T-3127, NOT A NEW FILING: an actual timed measurement
replicating T-3127's own four-arm probe against the NEW warm stage (i.e.
confirming a real `frob check --json` spawn against the stage returns
MEASURED, not just that the sweep receives the right directory) needs a
real git history with built natives and a real chunk-timing baseline --
infeasible inside a fast unit-test fixture, and is properly T-3127's OWN
acceptance criterion to re-verify against this change, since T-3127
already exists and already tracks exactly that measurement. No new
ticket filed for this -- T-3127 is the existing record.

Filed: T-3176 (docs kind) -- (1) document the warm stage in
docs/modules/tickets-landing.md#the-disposable-stage-flip-t-3121 (that
file was under another agent's live T-3163 scope lease for the whole of
this ticket's work, so a frob:waive AFFECT001 covers the gap instead of
forcing a cross-lease edit); (2) split _squash_apply_on_disposable_stage's
new ensure/compose/fallback branch into its own helper (frob:waive
ARCH001, 147 lines over the 60-line threshold) once that file's lease is
free.

GATES: `frob check --ticket T-3135` -- zero errors attributable to the
touched files (src/frob/tickets/_land.py,
tests/unit/test_land_stage_flip.py) after fixing SCOPE001 (test file
missing from declared scope -- the ticket's own scope named only
_land_cmd.py/_land.py, not the test file its own acceptance fixtures
needed), COV002 (frob:ticket directives on the 3 new test methods),
DOC007-adjacent AFFECT001/ARCH001 (waived with a real follow-up ticket,
not self-referential), and 3 E501 line-length errors in the waiver
comments themselves.

### Changed
```
 tickets/T-3135/done-report.md      | 88 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3135/ticket.md           | 15 ++++++-
 tickets/T-3176/ticket.md | 30 +++++++++++++
 3 files changed, 132 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_pre_commit_sweep_engages_the_warm_stage_not_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_warm_stage_reused_across_lands` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_warm_stage_unavailable_falls_back_to_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_root_never_goes_dirty_during_the_squash_apply` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_worktree_setup_failure_refuses_without_touching_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 125 error(s), 1113 warning(s), 874 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_evidence.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3135, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/__init__.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, missing-argument@tests/unit/test_coordinator_scripts.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
