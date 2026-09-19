---
id: T-4503
title: Add unity-project scaffold type (starter frob.toml + design/*.strata for an
  existing Unity project)
state: in-progress
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-4515
- T-4512
parent: T-4518
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/types/unity-project/**
- src/frob/scaffold/project.py
- tests/unit/test_scaffold_unity_project.py
- docs/commands/scaffold.md
- src/frob/scaffold/_unity_project.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_scaffold_unity_project.py
  reason: unit tests for the new render_unity_project function and its three acceptance
    criteria
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/commands/scaffold.md
  reason: render_unity_project is a new frob:doc docs/commands/scaffold.md#public-api
    symbol; the doc's own manifest table needs the unity-project entry
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/scaffold/_unity_project.py
  reason: 'LARGE001: project.py was already at exactly 800 lines before this diff;
    adding render_unity_project and its helpers pushed it to 949. Move the unity-project-specific
    rendering logic into its own sibling module.'
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: GIVEN an existing Unity project directory with two .asmdef files, WHEN 'frob
    scaffold unity-project' (or equivalent frob init detection) runs against it, THEN
    it writes a frob.toml with Unity's excludes pre-populated and one design/*.strata
    file per asmdef.
  evidence: []
- text: GIVEN the scaffold is run twice without --force, WHEN it detects existing
    frob.toml/design files, THEN it refuses (ScaffoldError.OutputExists) rather than
    silently overwriting.
  evidence: []
- text: GIVEN a directory that is not a Unity project, WHEN 'frob scaffold unity-project'
    is invoked against it, THEN it errors clearly rather than producing a bogus config.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add a 'unity-project' entry to src/frob/scaffold/project.py's manifest table (modeled on the existing python-library/cpp-library types) with .j2 templates under src/frob/scaffold/data/types/unity-project/ that, run against an EXISTING Unity project directory, produce a starter frob.toml plus design/*.strata files seeded with one strata component per detected .asmdef (from T-4512, blocked_by it) and the default excludes (from T-4515, blocked_by it).

GIVEN an existing Unity project directory with two .asmdef files, WHEN 'frob scaffold unity-project' (or equivalent frob init detection) runs against it, THEN it writes a frob.toml with Unity's excludes pre-populated and one design/*.strata file per asmdef.
GIVEN the scaffold is run twice without --force, WHEN it detects existing frob.toml/design files, THEN it refuses (ScaffoldError.OutputExists) rather than silently overwriting.
GIVEN a directory that is not a Unity project, WHEN 'frob scaffold unity-project' is invoked against it, THEN it errors clearly rather than producing a bogus config.