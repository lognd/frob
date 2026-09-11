---
id: T-4428
title: 'TICK006 still fires on T-4041: disclosure sentence still contains the literal
  draft id'
state: queued
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-4041/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: record the re-fire and the fix plan
  actor: logan
  at: '2026-09-11'
  old_length: 0
  new_length: 643
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TICK006 fired again on tickets/T-4041/done-report.md after T-4426 landed: the detector matches the literal ticket id T-draft-858a1bad, not the intent, and T-4426's disclosure sentence still names that id (in 'that draft was LOST before promotion... citing it here as T-draft-858a1bad'). Fix: reword the disclosure sentence in T-4041's Done report to name NO ticket id at all -- say something like 'a draft ticket that was never promoted and is lost; see T-4426' -- via frob ticket done-report (a ticket verb), not a hand-edit. Confirm with 'uv run frob check --only tick | grep TICK006' that the finding is gone. SCOPE: tickets/T-4041/** only.