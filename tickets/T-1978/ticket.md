---
id: T-1978
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
land_commit: null
---
T-1629 registered SYS110 in _KNOWN_GATE_RULES but the docs/modules/gates.md#rule-catalog frob:enumerates member list was not updated, regressing the unscoped floor 0 -> 1 (DOCENUM001). Add SYS110 to the enumerates member list. Same shape T-1958 fixed for the prior batch (T-1937).

## Done report

Added SYS110 to docs/modules/gates.md's frob:enumerates member list,
restoring the unscoped floor (DOCENUM001 0 -> 1 regression from T-1629's
land, same shape T-1958 fixed hours earlier). Docs-only single-line fix,
no code changed; existing CLI-dispatch integration test recorded as
evidence per the docs-only-ticket precedent.

### Changed
```
 docs/modules/gates.md              |  2 +-
 tickets/T-1978/ticket.md | 25 +++++++++++++++++++++++++
 2 files changed, 26 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 1130 warning(s), 709 waived
- error-findings: ARCH001@src/frob/tickets/_land.py
