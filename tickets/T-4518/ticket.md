---
id: T-4518
title: 'Unity project model: detection, walk-ignores, asmdef as strata nodes, scaffold,
  doctor'
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4513
tier: story
sprint: null
runs_last: false
milestone: 0.533.0
flavour: user_story
due: null
rank: null
points: 1
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4518
branch: t-4518
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
- field: points
  old_value: null
  new_value: '1'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_scaffold_unity_project.py::TestRenderUnityProject::test_writes_frob_toml_with_unity_excludes
- tests/unit/test_scaffold_unity_project.py::TestRenderUnityProject::test_one_strata_file_per_asmdef
- tests/test_excludes.py::TestUnityExcludeGlobs::test_unity_project_adds_globs
- tests/test_excludes.py::TestUnityExcludeGlobs::test_non_unity_project_adds_nothing
- tests/unit/test_lang_project_detect.py::test_detects_unity_project
- tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_env_reports_version
- tests/unit/test_scaffold_unity_project.py::TestOutputExistsRefusal::test_second_run_without_force_is_output_exists
- tests/unit/test_scaffold_unity_project.py::TestNotAUnityProject::test_plain_directory_is_not_a_unity_project
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: recognize and scaffold Unity projects. Parent for the four leaves below.

Deliverables: detect a Unity project by Assets/, Packages/manifest.json, ProjectSettings/ProjectVersion.txt; exclude Library/, Temp/, Logs/, obj/, *.meta from the walker; read each .asmdef as a strata component boundary (one strata node per asmdef by default); a 'unity-project' scaffold type or frob init detection producing a starter frob.toml + design/*.strata for an existing Unity project; frob doctor recognizing the Unity toolchain (Unity Hub / editor path, optional not required).