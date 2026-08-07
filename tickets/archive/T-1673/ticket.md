---
id: T-1673
title: SUITE-RESULT reports failure COUNTS but never the failing node ids
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/conftest.py
  reason: narrow scope to the SUITE-RESULT hook and its test file
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: narrow scope to the SUITE-RESULT hook and its test file
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_lists_failing_node_ids
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_caps_failing_node_ids_with_and_n_more
designated_repro_test: null
threat: null
component: null
---
The pytest_sessionfinish SUITE-RESULT hook added by T-1596 prints 'exitstatus=N collected=N failed=N' so a suite result is always visible regardless of how many -q flags are stacked. That solved visibility of the VERDICT but not of the CONTENT.

Observed 2026-08-06: a full coverage run reported 'SUITE-RESULT: exitstatus=3 collected=8654 failed=5'. Under stacked -q pytest emits no 'short test summary info' section, so the five failing node ids appeared NOWHERE in 452 seconds of output. The only actionable next step was to re-run the entire suite -- eight minutes -- purely to learn which tests to look at.

Fix: have the hook emit each failing node id (and its terminal outcome) on its own line, capped at a sane maximum with an 'and N more' tail. The whole point of the hook is that its output survives verbosity suppression; a count that cannot be acted on without a second full run does not meet that bar.

Same root shape as T-1596: a diagnostic that is technically present but not sufficient to act on is not a working diagnostic.