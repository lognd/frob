---
id: T-2246
title: Audit test-only quarantine seed helpers for WIRE001 exemption vs deletion
state: queued
kind: docs
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
frob:waive WIRE001 on tests/unit/verify/test_quarantine.py::_seed_stuck_store needs a live open follow_up ticket (WIRE002) but has no real wiring work pending -- it is a permanent test-only fixture helper, never meant to gain a production caller. Filed only to satisfy WIRE002's live-ticket requirement (T-2217's own land discovered this); either confirm the waiver's reasoning is permanent and this ticket can close as-is, or delete the helper if it turns out unused.