---
id: T-4526
title: Detect Unity projects and exclude Library/Temp/Logs/obj/*.meta from the walker
state: dropped
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-draft-e7dd275c
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/excludes.py
- src/frob/lang/_project_detect.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: wire testsuite fs.write via-list for new tmp_path-writing test file (Unity
    project detect)
  actor: logan
  at: '2026-09-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add Unity-project detection (Assets/, Packages/manifest.json, ProjectSettings/ProjectVersion.txt present) and wire Library/, Temp/, Logs/, obj/, *.meta into the exclude-globs machinery (src/frob/excludes.py) for a detected Unity project.

GIVEN a directory with Assets/, Packages/manifest.json, and ProjectSettings/ProjectVersion.txt, WHEN frob's project detection runs, THEN it identifies the root as a Unity project.
GIVEN a Unity project with a populated Library/ directory (Unity's build cache), WHEN frob walks the tree, THEN Library/, Temp/, Logs/, obj/ are excluded and no .meta file is treated as a source file.
GIVEN a plain (non-Unity) C# repo with no Assets/ directory, WHEN detection runs, THEN it is NOT misidentified as a Unity project.

## Drop reason
- 2026-09-16: duplicate record: T-4413's land promoted this draft to T-4515 on dev while the in-progress draft dir survived; the work lands as T-4515
