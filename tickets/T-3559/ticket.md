---
id: T-3559
title: Implement ledger-mirror pending-queue + flush batching (per T-3550 design,
  pending owner sign-off)
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: medium
blocked_by:
- T-3550
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/ticket_runner/_land.py
- src/frob/app/ticket_runner/_rapid_sweep.py
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
Implements docs/design/ledger-mirror-batching.md's pending-mirror-queue + per-event flush design (land completion / sweep completion / bounded timer triggers), reusing the T-3297 merge driver for the flush commit path. BLOCKED on an owner call the design document could not resolve on its own: whether a flush commit naming multiple tickets in one subject line is acceptable to the CrossTicketLeakage/scope-closure check family, or whether the flush must instead produce one commit per flushed ticket (batching only within-ticket, not across tickets) to avoid touching that family at all -- see the design doc's 'Hazard needing an owner call' section. Block this ticket on T-3550 until that sign-off is given.