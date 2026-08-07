---
id: T-1549
title: 'Tier-A auto-fix: ClaimDivergence re-run via done-report recap'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1531: a ClaimDivergence land refusal already has a documented manual recipe (re-run the ticket's done-report with its existing why text -- the recap re-measures the claim against current evidence). Wire a Tier-A handler that performs exactly that through the T-1262 verify-or-rollback transaction like every other handler here.