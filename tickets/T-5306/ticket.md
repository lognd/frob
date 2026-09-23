---
id: T-5306
title: 'WEBSEC101-108: output-encoding and template sinks'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5307
parent: T-5141
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_xss.py
- tests/fixtures/webapp/websec1xx/**
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
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule ids WEBSEC101 (reflected/stored XSS encoding, ASVS V1.2.1), 102 (innerHTML/outerHTML/document.write/insertAdjacentHTML JS/TS AST), 103 (dangerouslySetInnerHTML JSX), 104 (v-html Vue SFC), 105 (Jinja |safe/autoescape=False regex), 106 (Django mark_safe/autoescape-off Python AST + template regex), 107 (Rails .html_safe/raw() regex), 108 (PHP echo of superglobals without htmlspecialchars, regex). Dispatched by framework detection (WEBSUB-2) so a Django-only repo never runs the Rails rule. Fixture: one planted finding per rule id.