---
id: T-5307
title: 'WEBSEC injection substrate: sink/source registry (extends SEC005 taint gate)'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5141
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
- src/frob/gates/_taint_gate.py
- src/frob/webapp/_websec_sinks.py
- tests/fixtures/webapp/websec1xx/**
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Verified: SEC005's taint substrate exists (src/frob/gates/_taint_gate.py, docs/modules/gates.md#rule-catalog, T-0781) -- this leaf extends it, it does not invent a parallel engine. New src/frob/webapp/_websec_sinks.py registry keyed by framework: sources (request params/headers/body/URL/cookies/filenames across Flask/Django/Express/Rails/FastAPI), sinks (innerHTML/outerHTML/document.write/insertAdjacentHTML for JS/TS AST; dangerouslySetInnerHTML for JSX; v-html for Vue SFC template block; Jinja |safe/autoescape=False, Django mark_safe/autoescape-off, Rails .html_safe/raw() as TEXT-REGEX rules over template files, not tree-sitter). Fixture: tests/fixtures/webapp/websec1xx/ with one file per sink planting exactly the finding.