---
id: T-2783
title: 'Reformat batch 4/N: 10 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- src/frob/lang/_extract.py
- src/frob/lang/_support.py
- src/frob/perf/_harness.py
- src/frob/release/_cli.py
- src/frob/strata/_capacity.py
- src/frob/strata/_design_load.py
- src/frob/strata/_effects.py
- src/frob/strata/_threat.py
- tickets/T-2784/ticket.md
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
- op: remove
  glob: src/frob/gates/_wire.py
  reason: T-2778 holds a live lease on this file
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tickets/T-2784/ticket.md
  reason: dropped-draft ticket file left in this worktree's diff from the batch-4
    refiling; harmless residue, in-scope so SCOPE001 does not block the land
  actor: logan
  at: '2026-08-21'
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
land_commit: null
---
Batch 4/N of T-2359: apply ruff-format-only reformat to 10 files.
Excludes src/frob/gates/_tickets_gate.py, _waive.py, _profile_schema.py,
_rule_id_scan.py, _testing_schema.py (live T-2557 lease). No semantic
changes; format-only diff.