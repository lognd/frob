---
id: T-4337
title: docs/modules/verify-rapid-debt-visibility.md fails INV003/INV004/REF002
state: queued
kind: docs
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/verify-rapid-debt-visibility.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Found while working T-4319 (unrelated -- pre-existing on main from T-4324's
own land, not caused by T-4319's diff, and outside T-4319's declared scope
of src/frob/gates/_tickets_gate.py).

frob check reports 3 ERRORs against this file:
- INV003: makes an exclusivity/normative claim ("only") with no
  frob:invariant INV-### marker naming a real invariant.
- INV004: describes behavior ("never"/"only") with no matching coverage.
- REF002: has exactly one inbound reference (src/frob/app/verify_runner.py)
  -- a single point of anchor is fragile.

## Plan

Add the missing frob:invariant marker(s) for the claims INV003/INV004
flag, and either add a second real consumer/reference to the doc or
demote/waive REF002 with a reasoned justification if a single anchor is
correct here.