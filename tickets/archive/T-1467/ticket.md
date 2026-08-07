---
id: T-1467
title: clear T-1360/T-1462 land residue
state: dropped
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_core.py
- tests/test_capability_registry.py
- src/frob/app/telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
main has 4 live errors post T-1360/T-1462 land: (a) src/frob/vet/_capability_core.py:589 ty invalid-return-type -- function can implicitly return None but declares bool; (b) tests/test_capability_registry.py:339 imports _SPECIAL_CHECKS from frob.vet._capability but T-1462 split moved it; (c) src/frob/app/telemetry.py ARCH001 x2: timed_call (64 lines) and usage_report (82 lines) too long, need helper extraction.

## Drop reason
- 2026-08-02: duplicate draft, superseded by T-1465 with fuller scope