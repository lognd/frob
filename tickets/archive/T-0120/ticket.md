---
id: T-0120
title: 'perf: split long test in tests/system/test_cli_perf.py'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
designated_repro_test: null
threat: null
component: null
---
found while working T-0045: TestCheckOnlyPerf.test_perf001_fixture_warns_but_check_exits_zero is 38 lines, over the 30-line arch threshold. Out of scope for T-0045 (tests/test_perf.py only).