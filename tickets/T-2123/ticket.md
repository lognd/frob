---
id: T-2123
title: frob ticket new accepts an unacknowledged over-broad scope; enforcement point
  is missing at filing time, not just start
state: queued
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Coordinator measured 2026-08-11: 'frob ticket new --scope src/frob/app/ticket_runner/' (a whole-directory glob) was ACCEPTED, emitting 614 scope-closure warnings (8 shown, 606 collapsed). T-2094 (dropped, see its Done report) confirmed start-time enforcement already exists (T-1866) -- this is a DIFFERENT, earlier gap: the over-broad scope enters the ledger and can suppress the doable queue for other agents from the moment of filing, not just from start. Extend the same TICK009/large_glob_warnings breadth measure and scope_breadth_ack escape hatch T-1866 already established to the new_ticket path. Also: the collapsed-warning display (8 shown of 614) makes a catastrophic scope look like a minor nit -- severity/prominence should scale with the collapsed count.