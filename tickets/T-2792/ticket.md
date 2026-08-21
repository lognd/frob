---
id: T-2792
title: 'Reformat batch 8/N: 13 files pending ruff-format (T-2359 child)'
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
- tests/unit/test_process_lock.py
- tests/unit/test_process_reap.py
- tests/unit/test_require_python.py
- tests/unit/test_research_assets.py
- tests/unit/test_main_entry.py
- tests/unit/test_makefile_coverage.py
- tests/unit/test_native_table_schema.py
- tests/unit/test_test_table_schema.py
- tests/unit/test_gitattributes_crlf_normalization.py
- tests/unit/test_confinement_lattice.py
- tests/unit/test_cycle_runner_root_resolution.py
- tests/unit/test_cycle_waiver.py
- tests/unit/test_dup_core.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
- tests/unit/test_process_reap.py::TestReapActiveChildren::test_terminates_and_joins_active_children
- tests/unit/test_require_python.py::TestRequiredVersion::test_parses_a_real_requires_python_line
- tests/unit/test_research_assets.py::test_mcp_json_parses_and_declares_required_servers
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_sampled_source_files_are_pinned_to_lf
- tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl::test_absolute_literal_write_is_escaped
- tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_unwaived_cycle_reports
- tests/unit/test_dup_core.py::test_core_available_returns_bool
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle[src/pkg]
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 8/N of T-2359: apply ruff-format-only reformat to 13
independent unit test files. No semantic changes; format-only diff.