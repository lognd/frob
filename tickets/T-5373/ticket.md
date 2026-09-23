---
id: T-5373
title: 'COMPLY109-116: GDPR/international disclosures'
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
- src/frob/webapp/_comply_international.py
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
DSAR SLA (GDPR Art.12(3), one month), Art.13 identity/legal-basis/retention text, right-to-erasure endpoint (Art.17), storage-limitation/TTL schema check (Art.5(1)(e)) -- reuses 5148-4's migration-scan helper for the PII-retention-TTL-column check rather than building a second migration parser -- encryption-at-rest config, breach-notification runbook presence, EU AI Act Art.50 chatbot-notice, CASL/TCPA consent capture. Fixture per rule id.