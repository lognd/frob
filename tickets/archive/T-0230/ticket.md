---
id: T-0230
title: PERF00x findings anchor to enclosing def line, not the offending statement
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_perf.py::test_perf002_anchors_to_index_call_line_not_def_line
- tests/test_perf.py::test_perf004_anchors_to_sort_call_line_not_def_line
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 15: lithos audit.py:450 PERF002 while the .index() calls sit at 465-466; rust conformance.rs:31 PERF003 points at the fn signature. Report the call-site line. Feeds T-0161 (heuristic fixes) -- coordinate. Regression fixtures asserting the exact reported line.