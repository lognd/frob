---
id: T-4147
title: route FLAGCOV001 parser import through the target project's own interpreter
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_flag_coverage.py
- tests/unit/test_flag_coverage_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_flag_coverage.py
  reason: 'T-4147: FLAGCOV001''s resolve_dotted_symbol call sites need to resolve/build
    the parser and config in the TARGET project''s own interpreter, not frob''s --
    the fix lives in this gate module, reusing frob.process._project_tool'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_flag_coverage_gate.py
  reason: test coverage for the project-env resolution fix lives alongside the existing
    gate tests
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/gates.md
  reason: doc closure for flag_coverage_gate's existing frob:doc anchor
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: docs/modules/gates.md
  reason: 'revert: gates.md is a shared god-doc with every gate''s own anchor -- widening
    scope to it drags in hundreds of unrelated symbols (347 SCOPE002 closure warnings),
    same trap as T-4146''s __init__.py; leaving the existing FLAGCOV001 doc anchor
    as a known pre-existing SCOPE002 condition instead'
  actor: logan
  at: '2026-09-07'
evidence:
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_project_dependency_not_in_frobs_own_interpreter_still_resolves
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_now_fire_reports_the_genuinely_dropped_flag
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_this_repos_own_frob_toml_reports_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3887 F-012: FLAGCOV001 imports the target project's own parser (e.g. stpone.flash.cli:build_parser) from frob's own interpreter, so it cannot resolve for any non-frob project (reports UNRESOLVED). frob.process._project_tool (T-3887/T-4125) only covers SUBPROCESS spawns (uv run --project ...); an import is resolved in-process and needs a different mechanism (spawn a resolver subprocess in the project's env and pass the result back, or importlib against the project's own sys.path/venv site-packages). Enumerate every import/exec-in-frobs-interpreter site first (this is likely not the only one), then decide the mechanism. Off-repo fixture required per T-3887's own doctrine: verify against a project whose package is not importable from frob's interpreter.