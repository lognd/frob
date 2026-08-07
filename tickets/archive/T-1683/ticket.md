---
id: T-1683
title: DEAD001/OPAQUE001 findings need a per-symbol symref to avoid file-wide waiver
  amnesty
state: dropped
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_opaque.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_waiver_directly_above_symbol_suppresses_it
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_waiver_scoped_to_symbol_not_whole_file
designated_repro_test: null
threat: null
component: null
---
Found while working T-1663 (gate semantics classification pass).

DEAD001 (`_dead_symbols.py`) and OPAQUE001 (`_opaque.py`) are both
semantically decided (AST/graph resolved), not lexical -- but neither
finding attaches a per-symbol `symref` to its Violation. Without one,
`frob:waive DEAD001 reason="..."` or `frob:waive OPAQUE001 reason="..."`
placed anywhere in a flagged file waives the finding for the WHOLE FILE,
not the one symbol it was meant to excuse -- every other dead/opaque
symbol in that file silently stops being reported too (the same blast-
radius hazard T-1663's own body calls out for any symref-less rule).

Plan: thread a per-symbol `symref` through `DeadSymbolViolation`/
`OpaqueViolation` construction (both already resolve the specific symbol
under inspection internally -- this is exposing existing data, not new
analysis) so a waiver line binds to one symbol.

## Drop reason
- 2026-08-06: premise is stale: DEAD001 already carries a per-symbol symref (T-1651/T-1652, tests/test_gates.py::TestDeadSymbolGate::test_waiver_directly_above_symbol_suppresses_it) and OPAQUE001 already carries one too (T-1659, tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref and test_opaque_waiver_scoped_to_symbol_not_whole_file) -- both landed before this ticket's own work started. Verified directly: both regression tests pass on current main, and _match_waiver's symref-exact branch (src/frob/gates/_waive.py) is what makes them symbol-scoped, not file-wide. No remaining gap found for either rule; forcing a re-implementation would just duplicate work already done and tested. (absorbed by T-1659)