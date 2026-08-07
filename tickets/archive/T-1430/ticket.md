---
id: T-1430
title: 'WIRE001: detect a new keyword-only parameter no call site passes'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWireGate::test_new_kwonly_param_never_passed_is_flagged
- tests/test_gates.py::TestWireGate::test_new_kwonly_param_passed_at_call_site_is_not_flagged
designated_repro_test: null
threat: null
component: null
---
T-1428 (WIRE001/WIRE002) implements three of the four case shapes named in
its brief: a new function/method/class with no non-test caller, a new gate
rule id missing from _KNOWN_GATE_RULES, and a new CLI flag dest missing
from _config_external.py's copy lists.

The fourth shape -- a new keyword-only parameter no call site passes
(T-1384's own_obligations_clean, T-1399's gate_claims_verified, T-1391's
only_paths) -- is not implemented. It needs a signature-level before/after
diff (does this diff add a new parameter to an existing function's
signature, and does any call site pass it) that neither the text-scan
approach wire_gate uses for new symbols, nor the string-membership
approach it uses for CLI dests, actually covers: the function itself
already has callers (it is not new), so the "no non-test caller" check
wire_gate implements does not fire, and the new PARAMETER specifically
being unpassed is a different, narrower question this ticket did not
build a detector for.

Scope: extend src/frob/gates/_dead_symbols.py's wire_gate (or a sibling
gate) with a keyword-only-parameter-added-and-never-passed check, most
likely via frob.lang's existing per-symbol signature parsing plus a
before/after comparison against the diff's base revision (mirroring how
src/frob/tickets/_new_gate_rule_acceptance.py already reads a symbol's
text at a historical revision for a related purpose).