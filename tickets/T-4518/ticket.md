---
id: T-4518
title: 'Unity project model: detection, walk-ignores, asmdef as strata nodes, scaffold,
  doctor'
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4513
tier: story
sprint: v0.534.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/types/unity-project/**
- src/frob/scaffold/project.py
- src/frob/app/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: recognize and scaffold Unity projects. Parent for the four leaves below.

Deliverables: detect a Unity project by Assets/, Packages/manifest.json, ProjectSettings/ProjectVersion.txt; exclude Library/, Temp/, Logs/, obj/, *.meta from the walker; read each .asmdef as a strata component boundary (one strata node per asmdef by default); a 'unity-project' scaffold type or frob init detection producing a starter frob.toml + design/*.strata for an existing Unity project; frob doctor recognizing the Unity toolchain (Unity Hub / editor path, optional not required).