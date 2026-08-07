---
id: T-0246
title: 'PERF003 correlation: unwind one level of call parens in _operand_names (f(x)
  == g(y) joins)'
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
- tests/test_perf.py::test_perf003_fires_on_call_operand_join
- tests/test_perf.py::test_perf003_call_operand_join_stays_narrow_no_recursive_unwind
designated_repro_test: null
threat: null
component: null
---
T-0161 round-2 review follow-up (non-blocking boundary found by the reviewer): a real nested join comparing derived values -- f(x) == g(y) with x,y the loop variables inside call parens -- does not fire because _operand_names only unwinds bare identifiers and one bracket-pair subscript (a[i-1] == b[j-1] works). Extend the unwinding one level of call parens, symmetric with the subscript handling; keep the attribute-access narrowing (its 4 sibling-loop FP sites are documented in T-0161's Done report). Regression: derived-value join fires; the 4 FP classes stay silent.