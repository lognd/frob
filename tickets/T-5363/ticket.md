---
id: T-5363
title: 'COMPLY123-127: subscription/cancellation/commerce dark patterns'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5360
parent: T-5145
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/webapp/_comply_commerce.py
- tests/fixtures/webapp/comply1xx/commerce/**
- tests/unit/test_webapp_comply_commerce.py
- docs/modules/webapp-comply-commerce.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/comply1xx/**
  reason: 'narrow to the commerce leaf: siblings own comply1xx/gdpr (T-5373), comply1xx/sector
    (T-5370); add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/comply1xx/commerce/**
  reason: 'narrow to the commerce leaf: siblings own comply1xx/gdpr (T-5373), comply1xx/sector
    (T-5370); add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_webapp_comply_commerce.py
  reason: 'narrow to the commerce leaf: siblings own comply1xx/gdpr (T-5373), comply1xx/sector
    (T-5370); add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-comply-commerce.md
  reason: 'narrow to the commerce leaf: siblings own comply1xx/gdpr (T-5373), comply1xx/sector
    (T-5370); add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
16 CFR 425 click-to-cancel/equal-prominence cancel path, CAN-SPAM unsubscribe link + postal address in email templates, PCI SAQ-A scope check. Stripe webhook signature cross-refs T-5144-3, not duplicated. Route-table lint for subscribe/checkout without a comparable-depth cancel route; email-template regex/text-search. Fixture per rule id.