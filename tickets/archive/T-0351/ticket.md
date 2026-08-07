---
id: T-0351
title: 'structural PII/secrets: join PII010/SEC110 findings to std.pii/std.secrets
  declarations'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- tests/test_gates.py
- docs/modules/gates.md
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0351 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0351 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: T-0455 scope hygiene narrowed tests/** to tests/test_gates.py, the wrong
    mirrored path -- this family's actual test file (used as T-0207 predecessor's
    evidence) is tests/test_pii_structural_gate.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin::test_pii010_discharged_by_matching_carries_tag
- tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin::test_pii010_still_fires_when_no_declaration_covers_it
- tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin::test_sec110_discharged_by_secret_clearance_binding
- tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin::test_sec110_still_fires_with_no_design_directory
- tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin::test_load_declared_surface_empty_with_no_design_dir
designated_repro_test: null
threat: null
component: null
---
T-0207 follow-on: today PII010 (frob.gates._pii_structural) discharges only via a bare frob:waive; the ticket's intent was a join to a T-0154 std.pii carries tag on the owning strata Node, and SEC110 to a T-0082 std.secrets node, so a declared field/env-read never needs a waiver at all. Deferred from T-0207's scope (waiver-only discharge shipped instead).