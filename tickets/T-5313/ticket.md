---
id: T-5313
title: 'A11Y substrate: HTML/JSX/Vue accessibility-tree query helpers'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5302
parent: T-5146
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
scope:
- src/frob/webapp/_a11y_substrate.py
- tests/fixtures/webapp/a11y1xx/**
- docs/modules/webapp-a11y.md
- tests/unit/test_webapp_a11y_substrate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/webapp-a11y.md
  reason: own module doc, WEBSEC fan-out convention (docs/modules/gate-*.md idiom;
    docs/modules/webapp.md is a shared file 7 concurrent tickets must not touch)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_a11y_substrate.py
  reason: 'unit tests binding frob:tests to the new substrate module (brief: one test
    file under tests/unit/ per ticket)'
  actor: logan
  at: '2026-09-23'
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
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_webapp_a11y_substrate.py::test_elements_with_attribute_html_positive_control
- tests/unit/test_webapp_a11y_substrate.py::test_elements_missing_attribute_html_negative_control
- tests/unit/test_webapp_a11y_substrate.py::test_elements_with_attribute_jsx_positive_control
- tests/unit/test_webapp_a11y_substrate.py::test_elements_missing_attribute_jsx_negative_control
- tests/unit/test_webapp_a11y_substrate.py::test_heading_sequence_vue_positive_control
- tests/unit/test_webapp_a11y_substrate.py::test_heading_sequence_vue_negative_control_skips_a_level
- tests/unit/test_webapp_a11y_substrate.py::test_html_lang_positive_control
- tests/unit/test_webapp_a11y_substrate.py::test_html_lang_negative_control_missing_attribute
- tests/unit/test_webapp_a11y_substrate.py::test_elements_with_attribute_unsupported_language_errors
- tests/unit/test_webapp_a11y_substrate.py::test_attribute_queries_unsupported_language_errors[elements_with_attribute-args0]
- tests/unit/test_webapp_a11y_substrate.py::test_attribute_queries_unsupported_language_errors[elements_missing_attribute-args1]
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5313
branch: t-5313
---
Small internal tree-sitter query-helper library over the html/jsx/vue grammars (WEBSUB-1): element-with-attribute lookup (img[alt], input[aria-label]), heading-sequence walk, <html lang> lookup -- shared by every A11Y rule below instead of duplicated per-rule query strings. Fixture: one clean + one violating HTML/JSX/Vue sample per query shape.