---
id: T-draft-46574f02
title: 'DOCENUM001: SYS110 missing from gates.md rule-catalog enumerates list'
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1629 registered SYS110 in _KNOWN_GATE_RULES but the docs/modules/gates.md#rule-catalog frob:enumerates member list was not updated, regressing the unscoped floor 0 -> 1 (DOCENUM001). Add SYS110 to the enumerates member list. Same shape T-1958 fixed for the prior batch (T-1937).