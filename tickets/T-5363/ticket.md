---
id: T-5363
title: 'COMPLY123-127: subscription/cancellation/commerce dark patterns'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5145
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_comply_commerce.py
- tests/fixtures/webapp/comply1xx/**
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
16 CFR 425 click-to-cancel/equal-prominence cancel path, CAN-SPAM unsubscribe link + postal address in email templates, PCI SAQ-A scope check. Stripe webhook signature cross-refs T-5144-3, not duplicated. Route-table lint for subscribe/checkout without a comparable-depth cancel route; email-template regex/text-search. Fixture per rule id.