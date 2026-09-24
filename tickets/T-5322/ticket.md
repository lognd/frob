---
id: T-5322
title: 'A11Y129-135: redundant entry, accessible authentication, contrast'
state: in-progress
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
- src/frob/webapp/_a11y_forms_contrast.py
- tests/fixtures/webapp/a11y1xx/forms_contrast/**
- docs/modules/webapp-a11y-forms-contrast.md
- tests/unit/test_webapp_a11y_forms_contrast.py
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
  glob: tests/fixtures/webapp/a11y1xx/forms_contrast/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four accessibility
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-a11y-forms-contrast.md
  reason: doc file for this leaf + unit test file per shared brief item 7
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_a11y_forms_contrast.py
  reason: doc file for this leaf + unit test file per shared brief item 7
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-a11y-forms-contrast.md
  reason: doc file for this leaf + unit test file per shared brief item 7
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_a11y_forms_contrast.py
  reason: doc file for this leaf + unit test file per shared brief item 7
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
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_webapp_a11y_forms_contrast.py::test_contrast_ratio_black_on_white_is_21_to_1
- tests/unit/test_webapp_a11y_forms_contrast.py::test_contrast_ratio_is_symmetric
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_empty_frameworks_short_circuits
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y129_positive-violation.html-A11Y129-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y129_negative-clean.html-A11Y129-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y130_positive-A11Y130-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y130_negative-clean.html-A11Y130-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y131_positive-A11Y131-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y131_negative-A11Y131-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y132_positive-A11Y132-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y132_negative-clean.html-A11Y132-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y133_positive-A11Y133-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y133_negative-A11Y133-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y134_positive-A11Y134-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y134_negative-clean.css-A11Y134-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y135_positive-A11Y135-True]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y135_negative-clean.scss-A11Y135-False]
- tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_gate_discovers_forms_contrast_hook_end_to_end
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y130_negative-A11Y130-False]
  new_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y130_negative-clean.html-A11Y130-False]
  reason: gate hook signature changed to (ctx, frameworks) after T-5323 landed; fixture
    param now includes filename
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y132_negative-A11Y132-False]
  new_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y132_negative-clean.html-A11Y132-False]
  reason: gate hook signature changed to (ctx, frameworks) after T-5323 landed; fixture
    param now includes filename
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y134_negative-A11Y134-False]
  new_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y134_negative-clean.css-A11Y134-False]
  reason: gate hook signature changed to (ctx, frameworks) after T-5323 landed; fixture
    param now includes filename
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y135_negative-A11Y135-False]
  new_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y135_negative-clean.scss-A11Y135-False]
  reason: gate hook signature changed to (ctx, frameworks) after T-5323 landed; fixture
    param now includes filename
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y129_positive-A11Y129-True]
  new_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y129_positive-violation.html-A11Y129-True]
  reason: gate hook signature changed to (ctx, frameworks) after T-5323 landed; fixture
    param now includes filename
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y129_negative-A11Y129-False]
  new_node: tests/unit/test_webapp_a11y_forms_contrast.py::test_a11y_findings_fixture[a11y129_negative-clean.html-A11Y129-False]
  reason: gate hook signature changed to (ctx, frameworks) after T-5323 landed; fixture
    param now includes filename
  actor: logan
  at: '2026-09-23'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5322
branch: t-5322
---
Redundant entry across multi-step forms (SC 3.3.7, no autofill/prefill binding), accessible authentication (SC 3.3.8, CAPTCHA step with no alternative), contrast ratio (SC 1.4.3, WCAG relative-luminance formula over literal hex/rgb pairs in CSS -- needs CSS grammar, WEBSUB-1b). Ship the contrast-ratio computation as a reusable pure function -- T-5147 (SEO/WEBPERF) needs the same math. Fixture per rule id.