---
id: T-0975
title: test_stamp_baseline_only_chunk_records_without_stamping expects stale gate
  set (missing exhaustive_handling)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping
designated_repro_test: null
threat: null
component: null
---
Found while working T-0970: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping asserts received_gates[0] == frozenset({archgate, clones, perf}) but the gates-native chunk now also includes exhaustive_handling (a gate added to _STAGE_GROUPS/_ALL_GATES since this test was last updated). Update the expected frozenset to match current gate registration.