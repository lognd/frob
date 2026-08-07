---
id: T-0366
title: PERF004 waive tests/test_dup_prefilter.py:52 sorted-in-loop (T-0363 out-of-scope)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_dup_prefilter.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_prefilter.py::TestCharacteristicVector::test_identical_streams_have_identical_vectors
designated_repro_test: null
threat: null
component: null
---
found while working T-0363 (src/frob/** scope): tests/test_dup_prefilter.py:52 has an unwaived PERF004 finding (sorted() over each pair's own 2-tuple inside a nested loop, data differs per iteration so it cannot be hoisted -- constant O(1) work per pair). Out of T-0363's src/frob/** scope. Add frob:waive PERF004 with that reason.