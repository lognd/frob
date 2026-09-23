---
id: T-5321
title: 'A11Y116-128: keyboard, focus, target size, motion'
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
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_a11y_interaction.py
- tests/fixtures/webapp/a11y1xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
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
Skip link (SC 2.4.1), focus-visible not suppressed (outline:none without replacement -- needs CSS grammar, WEBSUB-1b), tabindex>0, aria-hidden on a focusable element, target size 24x24/44x44 CSS px (SC 2.5.8 -- needs CSS grammar), prefers-reduced-motion respected when animations exist (CSS grammar), autoplay media without controls, video without captions track. Fixture per rule id.