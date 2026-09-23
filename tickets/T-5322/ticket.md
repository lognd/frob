---
id: T-5322
title: 'A11Y129-135: redundant entry, accessible authentication, contrast'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5146
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_a11y_forms_contrast.py
- tests/fixtures/webapp/a11y1xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Redundant entry across multi-step forms (SC 3.3.7, no autofill/prefill binding), accessible authentication (SC 3.3.8, CAPTCHA step with no alternative), contrast ratio (SC 1.4.3, WCAG relative-luminance formula over literal hex/rgb pairs in CSS -- needs CSS grammar, WEBSUB-1b). Ship the contrast-ratio computation as a reusable pure function -- T-5147 (SEO/WEBPERF) needs the same math. Fixture per rule id.