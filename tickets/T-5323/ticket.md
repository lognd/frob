---
id: T-5323
title: 'A11Y101-115: non-text content, structure, forms'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5313
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
- src/frob/webapp/_a11y_structure.py
- tests/fixtures/webapp/a11y1xx/structure/**
- src/frob/gates/_a11y_gate.py
- docs/modules/webapp-a11y-structure.md
- src/frob/gates/__init__.py
- src/frob/webapp/_a11y_substrate.py
- docs/modules/webapp-a11y.md
- tests/unit/test_webapp_a11y_structure.py
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
  glob: tests/fixtures/webapp/a11y1xx/structure/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four accessibility
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_a11y_gate.py
  reason: own the a11y gate discovery+registration for the family, T-5323
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-a11y-structure.md
  reason: document the A11Y hook protocol, own doc file per SUBSTRATE-FANOUT brief
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/__init__.py
  reason: wire a11y job into the gate dispatch dict per gate-registration.md
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/webapp/_a11y_substrate.py
  reason: T-5422 residue on the substrate this leaf consumes
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-a11y.md
  reason: T-5422 residue on the substrate this leaf consumes
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_a11y_structure.py
  reason: unit test file for the new hook module, per brief item 'test file under
    tests/unit/'
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
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_webapp_a11y_structure.py::test_a11y101_missing_alt
- tests/unit/test_webapp_a11y_structure.py::test_a11y102_svg_missing_name
- tests/unit/test_webapp_a11y_structure.py::test_a11y103_skipped_heading_level
- tests/unit/test_webapp_a11y_structure.py::test_a11y104_duplicate_h1
- tests/unit/test_webapp_a11y_structure.py::test_a11y105_missing_title
- tests/unit/test_webapp_a11y_structure.py::test_a11y106_missing_lang
- tests/unit/test_webapp_a11y_structure.py::test_a11y107_empty_lang
- tests/unit/test_webapp_a11y_structure.py::test_a11y108_link_no_name
- tests/unit/test_webapp_a11y_structure.py::test_a11y109_button_no_name
- tests/unit/test_webapp_a11y_structure.py::test_a11y110_generic_link_text
- tests/unit/test_webapp_a11y_structure.py::test_a11y111_unlabeled_input
- tests/unit/test_webapp_a11y_structure.py::test_a11y112_missing_autocomplete
- tests/unit/test_webapp_a11y_structure.py::test_a11y113_duplicate_id
- tests/unit/test_webapp_a11y_structure.py::test_a11y114_invalid_role
- tests/unit/test_webapp_a11y_structure.py::test_a11y115_invalid_aria_attribute
- tests/unit/test_webapp_a11y_structure.py::test_no_framework_short_circuits_to_empty
- tests/unit/test_webapp_a11y_structure.py::test_a11y_gate_discovers_hook_and_scans_tracked_files
- tests/unit/test_webapp_a11y_structure.py::test_a11y_gate_no_framework_short_circuits_to_empty
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5323
branch: t-5323
---
alt on img/svg role=img (SC 1.1.1), heading order + single h1 (SC 1.3.1), page title present/non-empty (SC 2.4.2), html lang (SC 3.1.1), link/button accessible names (SC 2.4.4, no generic 'click here'), form-input label association, autocomplete on identity fields (SC 1.3.5), duplicate ids, invalid ARIA role/attribute pairs. Fixture per rule id via 5146-1's query helpers.