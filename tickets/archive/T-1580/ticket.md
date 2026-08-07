---
id: T-1580
title: fold docs/modules/gates_e501_autofix.md into docs/modules/gates.md
state: done
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
- docs/modules/gates_e501_autofix.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:bash -c "test ! -f docs/modules/gates_e501_autofix.md && grep -q E501 docs/modules/gates.md"
  exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
T-1547's E501 Tier-A auto-fix handler doc landed as a standalone page (docs/modules/gates_e501_autofix.md) because docs/modules/gates.md -- home to every other Tier-A handler's own writeup -- was under an in-progress T-1205 lease for T-1547's whole duration. T-1205 has landed and the lease is clear: fold that page's content into gates.md's existing '--fix Tier-A deterministic auto-fix handlers' section (matching the SYS100/SYS104 T-1531 precedent's own subsection shape), then delete the standalone page.