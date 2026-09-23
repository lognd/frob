---
id: T-5303
title: Wire CSS/SCSS grammar into frob.lang (contrast/target-size/hidden-text substrate)
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: ''
runs_last: false
milestone: 0.535.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- src/frob/lang/_walk_css.py
- tests/fixtures/lang/**
- docs/modules/lang.md
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
- field: milestone
  old_value: null
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: v0.535.0
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
NEW leaf (owner-added): A11Y (T-5146-3, T-5146-4) and SEO (T-5147-3) need a real CSS/SCSS grammar for contrast-ratio computation, outline:none detection, target-size box computation, and hidden-text (color==background/font-size:0/opacity:0) detection -- confirm tree-sitter-language-pack's css grammar covers SCSS syntax or pin a dedicated tree-sitter-scss grammar if not. Wire .css/.scss into _EXTENSION_TABLE the same way WEBSUB-1 wires html/js/jsx/vue; write a thin _walk_css.py walker. Positive-control fixture: tests/fixtures/lang/sample.{css,scss}. T-5146-3, T-5146-4, and T-5147-3 block on this leaf.