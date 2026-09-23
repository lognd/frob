---
id: T-5324
title: Accessibility-statement page + axe-core/pa11y tool-registry entries
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
- src/frob/webapp/_a11y_statement.py
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
Content-lint for the accessibility-statement page (W3C WAI required contents: commitment, standard applied WCAG 2.2 AA, contact, known limitations, measures, technical prerequisites, tested environments), same shape as T-5145-2's privacy-policy lint. Add _RELEVANT_TOOLS entries for axe-core/pa11y in src/frob/doctor.py (T-5139/T-3276 pattern, same as the existing cargo-audit entry): relevant_when = an HTML/JSX file exists AND a dynamic-only A11Y criterion (color-only meaning) is in scope; absence is a failing UNMEASURED RelevantToolFinding, never silently skipped.