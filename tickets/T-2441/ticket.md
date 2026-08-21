---
id: T-2441
title: Register bare PORT001 gate rule id in _waive.py _KNOWN_GATE_RULES
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
evidence_scope:
- tests/gates/test_rule_id_scan_branches.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete
- tests/test_gates.py::TestKnownGateRuleIds::test_bare_port001_registered
designated_repro_test: tests/test_gates.py::TestKnownGateRuleIds::test_bare_port001_registered
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3880e6c2aa818d3e8d0598660712133f08977ef6
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