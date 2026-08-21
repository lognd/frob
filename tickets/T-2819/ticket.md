---
id: T-2819
title: REF001/REF002 systematic collapse (glob entrypoints) + promote to error
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2369
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
- tests/unit/gates/test_refs.py
- docs/modules/gates.md
- docs/modules/tickets-data-storage.md
- docs/index.md
- docs/design/test005-ratchet-schedule.md
- docs/investigations/T-2782-land-serialization.md
- docs/investigations/T-2790-check-stage-profile.md
- docs/investigations/T-2796-backlog-reproduction.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given REF001/REF002, when frob check --json runs, then zero findings remain
  evidence: []
- text: given src/frob/gates/_refs.py's REF001/REF002 severity, when read, then it
    is ERROR not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2369: REF001 (275->0) and REF002 (6->0) both fully burned down and promoted WARN->ERROR. REG008 (18 remaining) stays on the parent T-2369 for a separate batch.