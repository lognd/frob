---
id: T-5321
title: 'A11Y116-128: keyboard, focus, target size, motion'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5313
- T-5303
parent: T-5146
tier: ticket
sprint: null
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
- src/frob/webapp/_a11y_interaction.py
- tests/fixtures/webapp/a11y1xx/interaction/**
- docs/modules/webapp-a11y-interaction.md
- tests/unit/test_webapp_a11y_interaction.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/a11y1xx/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four accessibility
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/webapp/a11y1xx/interaction/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four accessibility
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-a11y-interaction.md
  reason: doc + unit test per shared brief item 7 (scope narrowed to keep sibling
    leaves concurrent)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_a11y_interaction.py
  reason: doc + unit test per shared brief item 7 (scope narrowed to keep sibling
    leaves concurrent)
  actor: logan
  at: '2026-09-23'
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
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_empty_frameworks_short_circuits
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y116_positive-A11Y116-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y116_negative-A11Y116-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y117_positive-A11Y117-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y117_negative-A11Y117-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y118_positive-A11Y118-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y118_negative-A11Y118-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y119_positive-A11Y119-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y119_negative-A11Y119-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y120_positive-A11Y120-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y120_negative-A11Y120-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y121_positive-A11Y121-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y121_negative-A11Y121-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y122_positive-A11Y122-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y122_negative-A11Y122-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y123_positive-A11Y123-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y123_negative-A11Y123-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y124_positive-A11Y124-True]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_findings_fixture[a11y124_negative-A11Y124-False]
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_interaction_positive_control_returns_correct_rule
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_gate_discovers_a11y_interaction_hook
- tests/unit/test_webapp_a11y_interaction.py::test_a11y_gate_discovered_hook_fires_on_planted_violation
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_webapp_a11y_interaction.py::test_a11y_gate_discovers_a11y_interaction_hook_and_fires
  new_node: ''
  reason: test renamed/split into test_a11y_gate_discovers_a11y_interaction_hook +
    test_a11y_gate_discovered_hook_fires_on_planted_violation to avoid the unrelated
    T-5324 a11y_statement crash
  actor: logan
  at: '2026-09-23'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5321
branch: t-5321
---
Skip link (SC 2.4.1), focus-visible not suppressed (outline:none without replacement -- needs CSS grammar, WEBSUB-1b), tabindex>0, aria-hidden on a focusable element, target size 24x24/44x44 CSS px (SC 2.5.8 -- needs CSS grammar), prefers-reduced-motion respected when animations exist (CSS grammar), autoplay media without controls, video without captions track. Fixture per rule id.

## Reopen log
- 2026-09-23: earlier land attempt was refused on DOC006 after leaving state=done; dev's own ledger still has T-5321 in-progress, reopening the worktree's stale local state to match before a fresh land
- 2026-09-23: concurrent land-runner retry of the earlier queued entry finalized/closed T-5321 again while this worktree's evidence was being fixed; reopening to in-progress before a fresh land