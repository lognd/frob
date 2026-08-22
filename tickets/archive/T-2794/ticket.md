---
id: T-2794
title: 'Reformat batch 9/N: 13 files pending ruff-format (T-2359 child)'
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
- tests/unit/test_check_budget.py
- tests/unit/test_check_tool_unavailable.py
- tests/unit/test_cli_hygiene_checklist_t1556.py
- tests/unit/test_close_promote_drafts.py
- tests/unit/test_close_rel001_bump.py
- tests/unit/test_close_t1648_remainder.py
- tests/unit/test_coordinator_scripts.py
- tests/unit/test_dup_graph_table_schema.py
- tests/unit/test_fleet_runner.py
- tests/unit/test_fmt_wiring_reachability_t2761.py
- tests/unit/test_parse_runner_direct.py
- tests/unit/test_rapid_sweep.py
- tests/unit/test_reporting_t1648_remainder.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget
- tests/unit/test_check_tool_unavailable.py::TestToolUnavailableResult::test_shape_is_a_failing_diagnostic
- tests/unit/test_cli_hygiene_checklist_t1556.py::TestRenumberPositionalContractDocumented::test_old_positional_help_names_the_whole_ledger_fallback
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion::test_absent_pyproject_is_none
- tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard::test_clean_narrative_is_unaffected
- tests/unit/test_coordinator_scripts.py::TestLoadReport::test_reads_path
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key
- tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_status_table
- tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability::test_check_mode_reports_no_change_for_rust_file_under_its_own_width
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_missing_tool_exits_with_error
- tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_absent_baseline_reads_as_none_not_empty
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_detects_known_phrase
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 9/N of T-2359: apply ruff-format-only reformat to 13
independent unit test files. No semantic changes; format-only diff.