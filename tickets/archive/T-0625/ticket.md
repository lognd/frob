---
id: T-0625
title: 'arch: module dependency cycle detection (ARCH1xx)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0620
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_smells.py
- src/frob/graph/**
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_models.py
  reason: extend shared ArchCategory for module-dependency-cycle category
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_arch.py::TestModuleDependencyCycles::test_two_file_import_cycle_flagged
- tests/unit/test_arch.py::TestModuleDependencyCycles::test_acyclic_imports_not_flagged
designated_repro_test: null
threat: null
component: null
---
Detect import cycles across modules using the existing module-dependency graph (shared with T-0620's layering contract, do not fork a second graph builder). Report the cycle path. Acceptance: a fixture pair of modules importing each other fails; docs updated; explicitly reuses T-0620's graph builder (no duplicate import-resolution code).