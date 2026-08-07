---
id: T-0045
title: 'perf: split heat/profile long functions and clear PERF-rule self-flags'
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
- tests/test_perf.py::test_perf001_fires_on_list_membership_in_loop
designated_repro_test: null
threat: null
component: null
---
Refactor campaign: extract cohesive helpers in frob.perf._heat/_profile/_rules so no function trips PERF003/PERF004 or the long-function bar, preserving behavior. Accounts for the touched-set under frob check COV002.