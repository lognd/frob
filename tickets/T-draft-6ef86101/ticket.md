---
id: T-draft-6ef86101
title: Read .asmdef assemblies as strata component boundaries
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-draft-7e030cb3
parent: T-draft-e7dd275c
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_unity_asmdef.py
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
Parse Unity .asmdef JSON files and map each one to a strata component boundary (one strata node per asmdef by default), so capability checking and dependency rules can be declared per-assembly the way they are per-package elsewhere. blocked_by T-draft-7e030cb3 (Unity detection/walk must exist first so asmdef discovery has a project to scan).

GIVEN a Unity project with two .asmdef files (e.g. Runtime and Editor assemblies), WHEN strata elaborates the project, THEN it creates two distinct component nodes, one per asmdef.
GIVEN an asmdef's 'references' array naming another assembly, WHEN strata builds the dependency graph, THEN an edge is created between the two asmdef-derived nodes matching that reference.
GIVEN a .cs file not covered by any .asmdef (implicitly in Unity's default assembly), WHEN strata elaborates, THEN it is assigned to a default/implicit assembly node rather than dropped or erroring.