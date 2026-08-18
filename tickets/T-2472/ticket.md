---
id: T-2472
title: add GATERULE001 catalog entry to docs/modules/gates.md, drop the T-2448 land-time
  COV001 waiver
state: done
kind: docs
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:grep -c 'GATERULE001 (T-2448)' docs/modules/gates.md exit=0 sha256=4355a46b19d3
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6ee576e6c423c6d85ba79219d5098d77766c8387
---
GATERULE001 (landed as part of T-2448, wiring find_unregistered_rule_ids
into the standing sys gate) still needs its catalog entry in
docs/modules/gates.md. It currently carries a
frob:waive COV001 on gate_rule_registry_violations because that doc file
was under a live lease at land time.

Add the real catalog entry describing GATERULE001 (a gate rule id
constructed in code but not registered in _KNOWN_GATE_RULES) alongside
the other rule catalog entries in docs/modules/gates.md, then drop the
COV001 waiver on gate_rule_registry_violations now that the real doc
edge exists.