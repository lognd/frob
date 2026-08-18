---
id: T-2441
title: Register bare PORT001 gate rule id in _waive.py _KNOWN_GATE_RULES
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2388 (frob.gates._port_selfcheck, PORT001) constructs a THIRD gate
rule id, bare "PORT001" (Violation(rule="PORT001", ...) at
_port_selfcheck.py:347, the T-2391 fail-loudly UNRESOLVED case for an
unreadable/unparseable pyproject.toml [project].name), distinct from
the "PORT001-PATH" / "PORT001-IDENT" pair already registered in
src/frob/gates/_waive.py's _KNOWN_GATE_RULES.

Landing T-2388 fails at close time:
UnregisteredGateRuleConstructed: diff constructs gate rule id(s)
['PORT001'] not yet registered in _KNOWN_GATE_RULES at all (T-1937).

src/frob/gates/_waive.py is outside T-2388's declared scope
(scope: src/frob/gates/_port_selfcheck.py,
tests/unit/gates/test_port_selfcheck.py only), so T-2388 cannot fix
this itself without a scope widen. Add "PORT001" (bare) alongside
"PORT001-PATH"/"PORT001-IDENT" in _KNOWN_GATE_RULES, then retry
landing T-2388.
