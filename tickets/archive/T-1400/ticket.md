---
id: T-1400
title: 'TEST005 burn-down: src/frob/app remainder after T-1276 false-close (116 findings,
  ~50 unsampled runners)'
state: done
kind: feature
origin: human
created: '2026-08-01'
priority: medium
blocked_by:
- T-1398
- T-1399
- T-1401
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- tests/test_app*.py
- tests/unit/test_app*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/**
  reason: test-writing scope was omitted from the original ticket; parallel T-1415/T-1296
    strata burn-down tickets declared their test dir explicitly, this one didn't
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_app*.py
  reason: test-writing scope was omitted from the original ticket; parallel T-1415/T-1296
    strata burn-down tickets declared their test dir explicitly, this one didn't
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: tests/unit/**
  reason: narrow to actual app test files per the over-broad-glob warning
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_app*.py
  reason: narrow to actual app test files per the over-broad-glob warning
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget
- tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_matching_violation_is_attributed_to_its_symbol
- tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_violation_with_no_matching_symbol_is_dropped
- tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_two_violations_on_the_same_symbol_accumulate_both_rules
- tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable::test_renders_one_row_per_entry_with_smell_tag
- tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable::test_empty_entries_still_prints_header_and_unattributed
- tests/unit/test_perf_runner_t1400.py::TestCollectStacksFromFileRequiresFile::test_missing_file_exits_1_with_logged_error
- tests/unit/test_perf_runner_t1400.py::TestCollectStacksSamplerBranch::test_sampler_flag_dispatches_to_sampler_collector
- tests/unit/test_perf_runner_t1400.py::TestPrintFindingsAdvisoryLoop::test_renders_one_line_per_advisory
- tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_entry_for_a_different_file_is_skipped
- tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_entry_with_no_symbol_record_is_skipped
- tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_matching_entry_produces_a_gutter_at_the_symbols_start_line
- tests/unit/test_perf_runner_t1400.py::TestPersistRunUnresolvedSection::test_hit_with_unknown_section_id_is_skipped_without_error
- tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering::test_hot_without_json_renders_a_table_with_header_and_row
- tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering::test_hot_top_truncates_the_table_rows
designated_repro_test: null
acceptance:
- text: GIVEN the TEST005 join is fixed per T-1398 WHEN the app package is re-measured
    THEN every remaining finding is triaged as either a genuine gap (closed with a
    behavioral test) or an artifact (recorded, no test written)
  evidence:
  - tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default
  - tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget
  - tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_matching_violation_is_attributed_to_its_symbol
  - tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_violation_with_no_matching_symbol_is_dropped
  - tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_two_violations_on_the_same_symbol_accumulate_both_rules
  - tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable::test_renders_one_row_per_entry_with_smell_tag
  - tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable::test_empty_entries_still_prints_header_and_unattributed
  - tests/unit/test_perf_runner_t1400.py::TestCollectStacksFromFileRequiresFile::test_missing_file_exits_1_with_logged_error
  - tests/unit/test_perf_runner_t1400.py::TestCollectStacksSamplerBranch::test_sampler_flag_dispatches_to_sampler_collector
  - tests/unit/test_perf_runner_t1400.py::TestPrintFindingsAdvisoryLoop::test_renders_one_line_per_advisory
  - tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_entry_for_a_different_file_is_skipped
  - tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_entry_with_no_symbol_record_is_skipped
  - tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_matching_entry_produces_a_gutter_at_the_symbols_start_line
  - tests/unit/test_perf_runner_t1400.py::TestPersistRunUnresolvedSection::test_hit_with_unknown_section_id_is_skipped_without_error
  - tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering::test_hot_without_json_renders_a_table_with_header_and_row
  - tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering::test_hot_top_truncates_the_table_rows
threat: null
component: null
---
Successor to T-1276, which reached state=done on main against an unmet criterion (see T-1399). The work itself is real and unfinished: 116 TEST005 findings remain under src/frob/app/ and roughly 50 runner entrypoints were never sampled.

Deliberately blocked on T-1398 and T-1399. Dispatching this before the join defect is fixed would repeat the failure mode already observed three times today -- agents finding well-tested code reported at 0.0 percent and being pushed toward filler tests. Do not start it until the measured count is trustworthy.

Landed and verified by T-1276 before the false close, so this ticket does NOT need to redo them: _daemon_proxy lease paths, check_runner colorized formatter, and AppConfig.from_external/from_args.