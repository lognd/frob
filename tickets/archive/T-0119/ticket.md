---
id: T-0119
title: 'perf: split long functions in app/perf_runner.py (_heat_body, _annotate)'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/perf_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
designated_repro_test: null
threat: null
component: null
---
found while working T-0045: analyze_project flags _heat_body (42 lines) and _annotate (33 lines) over the 30-line threshold. Out of scope for T-0045 (src/frob/perf/** and tests/test_perf.py only).