---
id: T-4512
title: Read .asmdef assemblies as strata component boundaries
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-4515
parent: T-4518
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_unity_asmdef.py
- tests/unit/strata/test_unity_asmdef.py
- tests/fixtures/unity_sample_asmdef/**
- docs/strata/surface.md
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_unity_asmdef.py
  reason: unit tests for the asmdef->strata component mapping
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/unity_sample_asmdef/**
  reason: static fixture asmdef project for tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/strata/surface.md
  reason: doc anchors for new frob:doc directives in _unity_asmdef.py
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: raise stratamod fs.read/fs.write ceilings for _unity_asmdef.py's two new
    via-list sites
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_two_asmdefs_two_distinct_nodes
- tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_reference_by_name_resolves_to_edge
- tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_reference_by_guid_resolves_to_edge
- tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_default_assembly_node_always_present
designated_repro_test: null
acceptance:
- text: GIVEN a Unity project with two .asmdef files (e.g. Runtime and Editor assemblies),
    WHEN strata elaborates the project, THEN it creates two distinct component nodes,
    one per asmdef.
  evidence:
  - tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_two_asmdefs_two_distinct_nodes
- text: GIVEN an asmdef's 'references' array naming another assembly, WHEN strata
    builds the dependency graph, THEN an edge is created between the two asmdef-derived
    nodes matching that reference.
  evidence:
  - tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_reference_by_name_resolves_to_edge
  - tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_reference_by_guid_resolves_to_edge
- text: GIVEN a .cs file not covered by any .asmdef (implicitly in Unity's default
    assembly), WHEN strata elaborates, THEN it is assigned to a default/implicit assembly
    node rather than dropped or erroring.
  evidence:
  - tests/unit/strata/test_unity_asmdef.py::TestBuildComponentNodes::test_default_assembly_node_always_present
acceptance_amendments:
- op: remove
  index: 5
  old_text: GIVEN a Unity project with two .asmdef files (e.g. Runtime and Editor
    assemblies), WHEN strata elaborates the project, THEN it creates two distinct
    component nodes, one per asmdef.
  new_text: null
  reason: duplicate criterion from a LandInProgress retry loop
  actor: logan
  at: '2026-09-16'
- op: remove
  index: 4
  old_text: GIVEN a Unity project with two .asmdef files (e.g. Runtime and Editor
    assemblies), WHEN strata elaborates the project, THEN it creates two distinct
    component nodes, one per asmdef.
  new_text: null
  reason: duplicate criterion from a LandInProgress retry loop
  actor: logan
  at: '2026-09-16'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Parse Unity .asmdef JSON files and map each one to a strata component boundary (one strata node per asmdef by default), so capability checking and dependency rules can be declared per-assembly the way they are per-package elsewhere. blocked_by T-4515 (Unity detection/walk must exist first so asmdef discovery has a project to scan).

GIVEN a Unity project with two .asmdef files (e.g. Runtime and Editor assemblies), WHEN strata elaborates the project, THEN it creates two distinct component nodes, one per asmdef.
GIVEN an asmdef's 'references' array naming another assembly, WHEN strata builds the dependency graph, THEN an edge is created between the two asmdef-derived nodes matching that reference.
GIVEN a .cs file not covered by any .asmdef (implicitly in Unity's default assembly), WHEN strata elaborates, THEN it is assigned to a default/implicit assembly node rather than dropped or erroring.