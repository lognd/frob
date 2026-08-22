---
id: T-2773
title: 'Reformat batch 1/N: 15 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-20'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/diagnosis-nudge.py
- scripts/fleet_status.py
- src/frob/app/design_runner.py
- src/frob/app/profile_runner.py
- src/frob/app/pyfmt_runner.py
- src/frob/app/sys_runner.py
- src/frob/app/telemetry/__init__.py
- src/frob/app/telemetry/_footguns.py
- src/frob/app/telemetry/_usage.py
- src/frob/app/ticket_runner/_attach_backfill.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/app/worktree_runner.py
- src/frob/arch/_abstraction.py
- src/frob/check/_python.py
evidence_scope:
- tests/unit/test_app_runners.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_profile_runner.py
- tests/unit/test_pyfmt_runner.py
- tests/unit/test_app_sys_capacity.py
- tests/unit/test_app_sys_threats.py
- tests/unit/test_app_sys_trace.py
- tests/test_telemetry.py
- tests/unit/test_check.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
- tests/unit/test_ticket_new_related.py
- tests/unit/test_ticket_new_scope_plausibility.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/diagnosis-nudge.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: scripts/fleet_status.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/design_runner.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/profile_runner.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/__init__.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/_footguns.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/_usage.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_attach_backfill.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/arch/_abstraction.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/check/_python.py
  reason: batch 1 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1
- tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_configured_and_effective
- tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations
- tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination
- tests/test_telemetry.py::test_append_event_writes_one_json_line
- tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match
- tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 021799883e4a52bdf90e2fec6d9006498fa3e96f
---
Batch 1/N of T-2359's ruff-format-only reformat (T-2359 itself has 184
files currently pending, re-measured -- see T-2359's Done report history).
This child covers exactly the 15 files listed in its scope. Filed as a
child rather than landing against T-2359 directly because `frob ticket
land` closes its target ticket, and T-2359's own acceptance criteria
(zero files needing reformat repo-wide) cannot honestly bind until every
batch lands.