---
id: T-0121
title: 'perf: PERF001/PERF003 false-positive on tests/test_perf.py genexpr assertions'
state: dropped
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Dropped: resolved directly in T-0045. The reviewer correctly rejected deferring
this as an out-of-scope discovery -- tests/test_perf.py is explicitly in
T-0045's declared scope and its title is "clear PERF-rule self-flags", so this
was scope avoidance, not a genuine out-of-scope finding. Fixed by restructuring
test_heat_joins_pstats_rows_onto_symbol_spans to build `entries_by_ref = {entry.ref:
entry for entry in report.entries}` (one `for`, no `==`) and index it directly,
replacing the `[e.ref for e in report.entries]` list comp plus
`next(e for e in report.entries if e.ref == ...)` genexpr pair that tripped the
for_count>=2-plus-== heuristic. No remaining PERF001/PERF003 on this file. See
T-0045's Done report for full verification.