---
id: T-draft-a7cad1fa
title: 'A11Y substrate: HTML/JSX/Vue accessibility-tree query helpers'
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
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_a11y_substrate.py
- tests/fixtures/webapp/a11y1xx/**
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
Small internal tree-sitter query-helper library over the html/jsx/vue grammars (WEBSUB-1): element-with-attribute lookup (img[alt], input[aria-label]), heading-sequence walk, <html lang> lookup -- shared by every A11Y rule below instead of duplicated per-rule query strings. Fixture: one clean + one violating HTML/JSX/Vue sample per query shape.