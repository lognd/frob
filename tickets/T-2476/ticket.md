---
id: T-2476
title: drop the T-2448 COV001 waiver on gate_rule_registry_violations now that GATERULE001
  has a doc entry
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
- src/frob/gates/_rule_id_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:uv run pytest tests/gates/test_rule_id_scan_branches.py -q exit=0 sha256=8999741613eb
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: db059694b6c138afb974d97951c9c44c76804b51
---
T-2472 added the GATERULE001 catalog entry to docs/modules/gates.md
(## GATERULE001 (T-2448), with a frob:describes anchor on
gate_rule_registry_violations). That half is done and landed.

The second half T-2472 wanted -- adding the frob:doc edge on
gate_rule_registry_violations pointing at the new anchor, and dropping
the frob:waive COV001 on it -- could not be done in the same pass: as of
T-2472's own work, src/frob/gates/_rule_id_scan.py was under T-2454's
live in-progress lease, and T-2472's own scope was docs/modules/gates.md
only (widening it collided with that same lease).

Once the lease clears: add
  # frob:doc docs/modules/gates.md#gaterule001-t-2448
directly above gate_rule_registry_violations in
src/frob/gates/_rule_id_scan.py, then delete the frob:waive COV001
comment block immediately above it (the one whose reason cites T-2448
and "Follow-up: add the catalog entry once the lease clears" -- that
follow-up is now done). Verify COV001 stays clean afterward.