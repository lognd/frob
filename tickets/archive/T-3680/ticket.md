---
id: T-3680
title: 'self-gate floor (e): repo-wide ruff-format sweep'
state: done
kind: docs
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/check/__init__.py
- src/frob/lang/_walk_cuda.py
- src/frob/process/_reap.py
- src/frob/tickets/_live_tracker.py
- src/frob/vet/_capability_scan.py
- tests/conftest.py
- tests/gates/test_comment_placement.py
- tests/gates_suite/test_compliance.py
- tests/gates_suite/test_coverage.py
- tests/gates_suite/test_debt.py
- tests/gates_suite/test_doc.py
- tests/gates_suite/test_fix_engine.py
- tests/gates_suite/test_invariant.py
- tests/gates_suite/test_prework.py
- tests/gates_suite/test_protocol.py
- tests/gates_suite/test_run.py
- tests/gates_suite/test_sys.py
- tests/gates_suite/test_test_gate.py
- tests/gates_suite/test_tick.py
- tests/gates_suite/test_waive.py
- tests/gates_suite/test_wire.py
- tests/test_app_daemon_proxy.py
- tests/test_ci_workflow_matrix.py
- tests/test_clean.py
- tests/test_lang.py
- tests/test_ticket_merge_driver.py
- tests/test_tickets_scope_mutation.py
- tests/ticket_land_suite/conftest.py
- tests/ticket_land_suite/test_archive.py
- tests/ticket_land_suite/test_claim_close.py
- tests/ticket_land_suite/test_dirt_ownership.py
- tests/ticket_land_suite/test_draft.py
- tests/ticket_land_suite/test_land_core.py
- tests/ticket_land_suite/test_land_lock.py
- tests/ticket_land_suite/test_land_plan.py
- tests/ticket_land_suite/test_ledger_splice.py
- tests/ticket_land_suite/test_push.py
- tests/ticket_land_suite/test_release.py
- tests/ticket_land_suite/test_verify_intent.py
- tests/ticket_land_suite/test_verify_reset.py
- tests/ticket_land_suite/test_waive_deletion.py
- tests/ticket_land_suite/test_wip.py
- tests/unit/arch_suite/conftest.py
- tests/unit/arch_suite/test_complexity.py
- tests/unit/arch_suite/test_concurrency.py
- tests/unit/arch_suite/test_guards.py
- tests/unit/arch_suite/test_lang_adapters.py
- tests/unit/arch_suite/test_lsp.py
- tests/unit/arch_suite/test_misc.py
- tests/unit/arch_suite/test_type_design.py
- tests/unit/coordinator_suite/test_check_summary.py
- tests/unit/coordinator_suite/test_fleet_worktrees.py
- tests/unit/gates/test_port_selfcheck.py
- tests/unit/rapid_sweep_suite/test_attribution.py
- tests/unit/rapid_sweep_suite/test_baseline.py
- tests/unit/rapid_sweep_suite/test_commit.py
- tests/unit/rapid_sweep_suite/test_dispose.py
- tests/unit/rapid_sweep_suite/test_filing.py
- tests/unit/rapid_sweep_suite/test_sweep_run.py
- tests/unit/rapid_sweep_suite/test_worktrees.py
- tests/unit/strata/test_sys003_calibration.py
- tests/unit/test_arch.py
- tests/unit/test_conftest_console_ctrl_guard.py
- tests/unit/test_conftest_self_scan_fixture.py
- tests/unit/test_land_record_commit.py
- tests/unit/test_scaffold_project.py
- tests/unit/test_ticket_runner_gate_findings.py
- tests/unit/test_ticket_runner_venv_sync_t3320.py
- tests/vet_suite/test_capability_scan_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:ruff format --check . exit=0 sha256=12f8f1fef65c
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Self-gate floor bucket (e): repo-wide ruff-format sweep.

`ruff format --check .` currently shows 71 files would be reformatted
(was 70 at the CI evidence run 33545437868; drift grew by one file
since). No worktree leases are live at filing time (`fleet_status.py`
shows 0 live leases) so no file needs to be excluded.

Fix: run `ruff format .` (or `frob fmt` if that is the canonical
formatter verb) across the whole tree. Mechanical, whitespace/wrap-only
-- no logic edits.

Evidence: `ruff format --check .` reports 0 files needing reformat
afterward.