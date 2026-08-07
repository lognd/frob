---
id: T-1372
title: 'Drain DOC006 to zero: unresolvable file::symbol and doc-anchor pointers'
state: done
kind: docs
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- CHANGELOG.md
- invariants/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: invariants/**
  reason: DOC006 findings include invariants/*.md doc pointers; same fix class as
    docs/**
  actor: logan
  at: '2026-08-01'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob check --only docanchor --only doclink --only docblocks exit=0 sha256=b059e00a874a
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN frob check --only gates runs THEN gate:DOC reports 0 DOC006
    warnings
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
55 findings at drive start. Two shapes: file::symbol pointers naming symbols that no longer resolve (often renamed or made private), and doc-anchor links whose target heading does not exist. Fix the reference where the target still exists under a new name; waive with a reason only where the pointer documents genuine history (e.g. CHANGELOG entries naming since-deleted symbols).