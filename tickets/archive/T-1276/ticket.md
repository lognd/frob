---
id: T-1276
title: 'TEST005 burn-down: src/frob/app (115 findings, 63 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
blocked_by:
- T-1320
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/app/**
- tests/app/**
- tests/unit/**
- tests/test_*.py
- tests/unit/test_doctor_runner_t1276.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/**
  reason: 'widen tests scope to match repo convention: app-package tests live under
    tests/unit/test_app_runners_*.py and tests/test_*.py, not a literal tests/app/
    directory

    '
  actor: logan
  at: '2026-07-31'
- op: add
  glob: tests/test_*.py
  reason: 'widen tests scope to match repo convention: app-package tests live under
    tests/unit/test_app_runners_*.py and tests/test_*.py, not a literal tests/app/
    directory

    '
  actor: logan
  at: '2026-07-31'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: 'widen tests scope to match repo convention: app-package tests live under
    tests/unit/test_app_runners_*.py and tests/test_*.py, not a literal tests/app/
    directory

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_plain_prints_all_available_and_does_not_exit
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_json_emits_parseable_report
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_plain_exits_1_and_prints_remediation
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_no_remediation_prints_empty_not_none
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_json_exits_1
- tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close
- tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_disabled_env_bypasses_lease
- tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_no_daemon_falls_back_unreachable
- tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_wedged_does_not_spawn_a_rival
- tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_orphaned_clears_socket_then_spawns
- tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_debug_passes_through_unchanged
- tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_info_passes_through_unchanged
- tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_warning_is_painted_yellow_when_color_on
- tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_error_is_painted_red_when_color_on
- tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_error_is_unpainted_when_color_off
- tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_critical_uses_the_error_branch_too
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_missing_file_falls_back_to_defaults
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_reads_and_merges_tool_frob_table
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_subcommand_is_resolved_to_the_enum
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_no_color_flag_is_copied_when_present
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_string_field_from_the_first_copy_loop_is_carried
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_bool_flag_from_the_second_copy_loop_defaults_false
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_bool_flag_from_the_second_copy_loop_is_set_true
- tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default
designated_repro_test: null
acceptance:
- text: GIVEN the app package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/app/**
  evidence:
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_plain_prints_all_available_and_does_not_exit
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_json_emits_parseable_report
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_plain_exits_1_and_prints_remediation
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_no_remediation_prints_empty_not_none
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_json_exits_1
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_disabled_env_bypasses_lease
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_no_daemon_falls_back_unreachable
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_wedged_does_not_spawn_a_rival
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_orphaned_clears_socket_then_spawns
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_debug_passes_through_unchanged
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_info_passes_through_unchanged
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_warning_is_painted_yellow_when_color_on
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_error_is_painted_red_when_color_on
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_error_is_unpainted_when_color_off
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_critical_uses_the_error_branch_too
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_missing_file_falls_back_to_defaults
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_reads_and_merges_tool_frob_table
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_subcommand_is_resolved_to_the_enum
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_no_color_flag_is_copied_when_present
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_string_field_from_the_first_copy_loop_is_carried
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_bool_flag_from_the_second_copy_loop_defaults_false
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_bool_flag_from_the_second_copy_loop_is_set_true
  - tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default
- text: GIVEN a 0.0%-branch symbol in app WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_plain_exits_1_and_prints_remediation
- text: GIVEN a new test added to close a app TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_plain_prints_all_available_and_does_not_exit
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_json_emits_parseable_report
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_plain_exits_1_and_prints_remediation
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_no_remediation_prints_empty_not_none
  - tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_json_exits_1
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_disabled_env_bypasses_lease
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_no_daemon_falls_back_unreachable
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_wedged_does_not_spawn_a_rival
  - tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_orphaned_clears_socket_then_spawns
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_debug_passes_through_unchanged
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_info_passes_through_unchanged
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_warning_is_painted_yellow_when_color_on
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_error_is_painted_red_when_color_on
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_error_is_unpainted_when_color_off
  - tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter::test_critical_uses_the_error_branch_too
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_missing_file_falls_back_to_defaults
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_reads_and_merges_tool_frob_table
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_subcommand_is_resolved_to_the_enum
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_no_color_flag_is_copied_when_present
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_string_field_from_the_first_copy_loop_is_carried
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_bool_flag_from_the_second_copy_loop_defaults_false
  - tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_bool_flag_from_the_second_copy_loop_is_set_true
  - tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default
threat: null
component: null
---
Package: src/frob/app (or the listed root modules).
TEST005 findings at current baseline: 115 total, 63 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
fleet_runner.py :: run
gitlog_runner.py :: run
vet_runner.py :: run
stats_runner.py :: run
arch_runner.py :: run
deprecated_runner.py :: run
telemetry.py :: is_disabled
telemetry.py :: iso_now
telemetry.py :: redact_command
telemetry.py :: append_event
telemetry.py :: tree_hash
telemetry.py :: estimate_tokens
telemetry.py :: record_cli_event
telemetry.py :: record_ticket_event
telemetry.py :: timed_call
perf_runner.py :: run
dup_runner.py :: run
xref_runner.py :: run
clean_runner.py :: run
_daemon_proxy.py :: ensure_daemon
_daemon_proxy.py :: query
_daemon_proxy.py :: _LeaseConnection.call
_daemon_proxy.py :: _LeaseConnection.close
_daemon_proxy.py :: try_daemon_lease
_daemon_proxy.py :: release_daemon_lease
worktree_runner.py :: run
parse_runner.py :: run
deploy_runner.py :: run
config.py :: AppConfig.from_external
config.py :: AppConfig.from_args
config.py :: load_arch_config
config.py :: stale_install_warning
scaffold_runner.py :: run
check_runner.py :: _ColorizedLevelFormatter.format
check_runner.py :: run
ack_runner.py :: run
doctor_runner.py :: run
natives_runner.py :: run
_snapshot.py :: load_or_build_snapshot
debt_runner.py :: run
... (23 more, see frob check --only test for the full list)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

## Failure log
- 2026-07-29 attempt 1: baseline (115 findings/63 at 0.0pct) is stale: sampled 17 of the 63 listed 0.0-branch symbols via targeted pytest --cov runs (fleet_runner, gitlog_runner, arch_runner, vet_runner, dup_runner, natives_runner, deploy_runner, parse_runner, agent_runner, clean_runner, debt_runner, deprecated_runner, fmt_runner, pool_runner, worktree_runner, telemetry.py x9 fns) and all already show 68-100pct real branch coverage via existing dedicated tests (tests/test_debt_runner.py, tests/test_deprecated_runner.py, tests/test_pool_runner.py, tests/test_worktree_guard.py, tests/unit/test_app_runners_t0875_leaf_collision.py, tests/test_telemetry.py, tests/unit/test_fleet_runner.py, etc); a fresh full-suite coverage stamp (coordinator-only per playbook 6b -- confirmed empirically, a 540s-timeout scoped --cov run for the whole app package still SIGTERMed mid-write) is needed to re-derive the real remaining TEST005 list before further test-writing work in this ticket is worth doing