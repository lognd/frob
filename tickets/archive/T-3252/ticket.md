---
id: T-3252
title: Consolidate duplicate _load_conftest test helper once T-3244's lease clears
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_conftest_suite_result_status.py
- tests/unit/_conftest_test_helpers.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/_conftest_test_helpers.py
  reason: T-3252's DUP001 fix extracts the shared _load_conftest loader into this
    new file, imported by both consolidated test files
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): pure test-code deduplication: identical _load_conftest
    logic extracted into a shared helper, both call sites'' behavior unchanged'
  actor: logan
  at: '2026-08-29'
  old_length: 531
  new_length: 694
evidence:
- tests/unit/test_conftest_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_lists_failing_node_ids
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_format_is_unchanged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 248ac3546d521bd11c3da37eaa257adafc273e8d
---
T-3246 added tests/unit/test_conftest_suite_result_status.py with its own _load_conftest helper (95% similar to the pre-existing one in tests/unit/test_conftest_stackdump.py, DUP001) because test_conftest_stackdump.py was under a live scope lease held by T-3244 (unrelated platform-safety burn-down) at land time and could not be edited. Once T-3244 lands/releases the lease, extract the shared loader into one helper (e.g. a small tests/unit/_conftest_test_helpers.py) and have both test files import it, removing the duplication.

frob:no-behavior-change reason="pure test-code deduplication: identical _load_conftest logic extracted into a shared helper, both call sites' behavior unchanged"