---
id: T-4148
title: route frob.testing coverage pytest spawn and xdist check through project env
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_coverage_refresh.py
  reason: 'T-4148: the bare pytest argv (F-017) and the xdist plugin-presence check
    (F-018) both need to route through the target project''s own uv-managed environment
    instead of frob''s'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: F-018's xdist-plugin-presence probe (_xdist_plugin_present) lives here and
    needs the same project-env fix
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_coverage.py
  reason: test coverage for the coverage_refresh pytest-argv fix
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/tickets/_worktree_guard.py
  reason: 'reverting: warn_if_xdist_plugin_missing''s exact frob-interpreter-scoped
    check is pinned by 3 zero-arg monkeypatch tests in tests/test_worktree_guard.py,
    which is under an active lease (T-3936) this ticket must not touch; fixing it
    safely needs either that lease clearing or a coordinated edit with T-3936. F-017
    (the bare pytest spawn) is the dominant, three-times-reported symptom and is fully
    fixed in _coverage_refresh.py; a plugin genuinely missing in the project env now
    surfaces as a real pytest exit-4 usage error through the real project-env spawn
    (already-existing UNMEASURED handling), not a silent green -- F-018''s preflight-message
    polish is filed as a follow-up instead of forced through a leased file'
  actor: logan
  at: '2026-09-07'
evidence:
- tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_off_repo_project_not_importable_from_frob
- tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_routes_through_project_env
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3887 F-017/F-018: frob coverage --full spawns a bare pytest from frob's own environment (F-017), and coverage refresh assumes pytest-xdist is installed in frob's environment, not necessarily the project's (F-018). frob.process._project_tool (T-3887/T-4125) routes ty/ruff spawns through uv run --project <root>; frob.testing._coverage_refresh's own pytest invocation(s) need the same treatment -- check first whether frob.process._pytest_spawn (referenced in docs/modules/process.md's pytest-spawn-resolution-t-3311 section) already covers this partially. Missing pytest-xdist in the PROJECT's env must be a loud typed error naming pytest-xdist and its install command, never a silent frob-env fallback or a silent loss of parallelism.