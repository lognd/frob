---
id: T-1022
title: 'EXHAUST001/002 turn-on debt burn-down: 190 escape-hatch sites (135 unknown-escape,
  55 named-escape)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/
- src/frob/gates/_exhaustive_handling.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check_tool_unavailable.py::TestToolCrashResult::test_shape_is_a_failing_diagnostic
- tests/unit/test_check_tool_unavailable.py::TestNativeCrashIsTypedResult::test_run_cargo_unexpected_crash_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestNativeCrashIsTypedResult::test_run_cargo_test_unexpected_crash_returns_failing_result
- tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
- tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_logs_with_exc_info
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_file_in_skipped_dir_is_not_added
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_file_matching_exclude_glob_is_not_added
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_python_file_with_matching_lang_is_added
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_python_file_wrong_requested_lang_is_skipped_after_node_add
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_nonmatching_nonempty_exclude_globs_does_not_short_circuit
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_cpp_file_requested_as_cpp_is_scanned_as_cpp
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_cpp_file_requested_as_python_is_not_scanned
- tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_plain_python_file_default_lang_is_scanned
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check THEN EXHAUST001+EXHAUST002 warnings are zero or reduced
    to a ticketed, justified residue
  evidence:
  - tests/unit/test_check_tool_unavailable.py::TestToolCrashResult::test_shape_is_a_failing_diagnostic
threat: null
component: null
---
T-0688 landed EXHAUST001/002 at WARN posture. Burn down the 190 sites: EXHAUST001 (unresolvable call/raise escapes a partial handler -- add catch-all or narrow the Unknown via frob:callee-raises), EXHAUST002 (named exceptions escape uncaught/undeclared -- catch or declare frob:raises). Errors-as-values discipline: prefer typani Result returns at real fallible boundaries over blanket except Exception. If a systematic FP class emerges in the resolver, fix the resolver first and report before/after counts.