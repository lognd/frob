---
id: T-5369
title: Lighthouse tool-registry entry for dynamic-only Core Web Vitals measurement
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5364
- T-5301
parent: T-5147
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
- docs/modules/gates.md
- docs/guides/install.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
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
_RELEVANT_TOOLS entry for lighthouse (T-5139 pattern, same shape as 5146-5's axe-core/pa11y entries): relevant_when = a web framework is detected (WEBSUB-2) AND a Core Web Vitals rule is in scope; absence is a failing UNMEASURED RelevantToolFinding.