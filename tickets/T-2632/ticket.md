---
id: T-2632
title: 'test_mutation_sweep_queue.py: test_counts_only_pending_entries red on main'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_mutation_sweep_queue.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries
designated_repro_test: tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 931195c5909ea741b8a6ec7206c114e2882f812b
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries
fails with a bare `assert False` -- pytest's short summary gives no
further detail from the top-level failure line alone; needs the full
traceback read to classify. Not investigated further in T-2623 due to a
time-boxed land window.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).