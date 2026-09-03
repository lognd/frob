## Done report

Ran `ruff format .` across the whole tree -- 71 files reformatted (70
at the CI evidence run, one more accumulated since), 1357 left
unchanged. Whitespace/wrap-only, no logic edits. No worktree leases
were live at filing/land time so nothing needed to be excluded.

Evidence: `ruff format --check .` -- 0 files needing reformat, all
1428 files already formatted.

### Changed
```
 .claude/hooks/root-write-guard.py                  |   1 +
 src/frob/app/ticket_runner/_land_cmd.py            |   4 +-
 src/frob/check/__init__.py                         |   6 +-
 src/frob/lang/_walk_cuda.py                        |   4 +-
 src/frob/process/_reap.py                          |   2 -
 src/frob/tickets/_live_tracker.py                  |  18 ++-
 src/frob/vet/_capability_scan.py                   |   4 +-
 tests/conftest.py                                  |  10 +-
 tests/gates/test_comment_placement.py              |   4 +-
 tests/gates_suite/test_compliance.py               |   8 +
 tests/gates_suite/test_coverage.py                 |   8 +
 tests/gates_suite/test_debt.py                     |   4 +
 tests/gates_suite/test_doc.py                      |   9 +-
 tests/gates_suite/test_fix_engine.py               |   6 +-
 tests/gates_suite/test_invariant.py                |   9 +-
 tests/gates_suite/test_prework.py                  |   8 +
 tests/gates_suite/test_protocol.py                 |   8 +
 tests/gates_suite/test_run.py                      |   8 +-
 tests/gates_suite/test_sys.py                      |  23 ++-
 tests/gates_suite/test_test_gate.py                |   8 +
 tests/gates_suite/test_tick.py                     |   6 +
 tests/gates_suite/test_waive.py                    |  19 ++-
 tests/gates_suite/test_wire.py                     |   6 +
 tests/test_app_daemon_proxy.py                     |   4 +-
 tests/test_ci_workflow_matrix.py                   |  12 +-
 tests/test_clean.py                                |   4 +-
 tests/test_lang.py                                 |   4 +-
 tests/test_ticket_merge_driver.py                  |  16 +-
 tests/test_tickets_scope_mutation.py               |   3 +-
 tests/ticket_land_suite/conftest.py                | 178 +--------------------
 tests/ticket_land_suite/test_archive.py            |   5 -
 tests/ticket_land_suite/test_claim_close.py        |  21 ---
 tests/ticket_land_suite/test_dirt_ownership.py     |   5 -
 tests/ticket_land_suite/test_draft.py              |   5 -
 tests/ticket_land_suite/test_land_core.py          |  11 --
 tests/ticket_land_suite/test_land_lock.py          |   5 +-
 tests/ticket_land_suite/test_land_plan.py          |   4 -
 tests/ticket_land_suite/test_ledger_splice.py      |   9 --
 tests/ticket_land_suite/test_push.py               |   6 -
 tests/ticket_land_suite/test_release.py            |   5 -
 tests/ticket_land_suite/test_verify_intent.py      |   7 +-
 tests/ticket_land_suite/test_verify_reset.py       |   9 --
 tests/ticket_land_suite/test_waive_deletion.py     |   1 -
 tests/ticket_land_suite/test_wip.py                |   3 -
 tests/unit/arch_suite/conftest.py                  |   2 +-
 tests/unit/arch_suite/test_complexity.py           |   1 -
 tests/unit/arch_suite/test_concurrency.py          |   2 -
 tests/unit/arch_suite/test_guards.py               |   3 -
 tests/unit/arch_suite/test_lang_adapters.py        |   1 -
 tests/unit/arch_suite/test_lsp.py                  |   1 -
 tests/unit/arch_suite/test_misc.py                 |   1 -
 tests/unit/arch_suite/test_type_design.py          |   1 -
 tests/unit/coordinator_suite/test_check_summary.py |   5 -
 .../unit/coordinator_suite/test_fleet_worktrees.py |   2 +
 tests/unit/gates/test_port_selfcheck.py            |   4 +-
 tests/unit/rapid_sweep_suite/test_attribution.py   |   7 +-
 tests/unit/rapid_sweep_suite/test_baseline.py      |   6 +-
 tests/unit/rapid_sweep_suite/test_commit.py        |   7 -
 tests/unit/rapid_sweep_suite/test_dispose.py       |   6 -
 tests/unit/rapid_sweep_suite/test_filing.py        |   3 -
 tests/unit/rapid_sweep_suite/test_sweep_run.py     |   4 -
 tests/unit/rapid_sweep_suite/test_worktrees.py     |   2 -
 tests/unit/strata/test_sys003_calibration.py       |   4 +-
 tests/unit/test_arch.py                            | 159 ------------------
 tests/unit/test_conftest_console_ctrl_guard.py     |   8 +-
 tests/unit/test_conftest_self_scan_fixture.py      |   3 +-
 tests/unit/test_land_record_commit.py              |   8 +-
 tests/unit/test_scaffold_project.py                |   6 +-
 tests/unit/test_ticket_runner_gate_findings.py     |   4 +-
 tests/unit/test_ticket_runner_venv_sync_t3320.py   |   4 +-
 tests/vet_suite/test_capability_scan_python.py     |   2 +-
 tickets/T-3680/ticket.md                           |   2 +
 72 files changed, 181 insertions(+), 577 deletions(-)
```

### Evidence
- `cmd:ruff format --check . exit=0 sha256=12f8f1fef65c` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 26 error(s), 4701 warning(s), 908 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/check/__init__.py, COV003@tests/test_ci_workflow_matrix.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, DRIFT002@tests/system/test_frob_self_model.py, LANG004@src/frob/lang/_support.py, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, PRE001@tickets/T-3680, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json, unresolved-import@src/frob/arch/_abstraction.py, unresolved-import@src/frob/gates/_vmodel.py, unresolved-import@src/frob/graph/_core.py, unresolved-import@tests/test_arch_near_duplicate_native.py, unresolved-import@tests/unit/strata/test_capacity.py, unresolved-import@tests/unit/strata/test_strata_core_gil.py, unresolved-import@tests/unit/test_arch_python_native.py, unresolved-import@tests/unit/test_capability_native.py, unresolved-import@tests/unit/test_dup_core.py, unresolved-import@tests/unit/test_extract_native.py, unresolved-import@tests/unit/test_frob_core_gil.py, unresolved-import@tests/unit/test_lang_strata.py
