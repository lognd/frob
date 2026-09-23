---
id: T-5107
title: test_scaffold_dx._subprocess_env leaks PYTHONPATH into scaffolded uv run subprocess
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_scaffold_dx.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
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
While binding evidence for T-4763 (scaffold python-tool: typani floor), test_python_toolchain_scaffold_passes_check_immediately[python-tool] failed under frob ticket evidence (and under a plain PYTHONPATH=<worktree>/src python -m pytest invocation matching this repo's own agent-env recipe, T-4459).

Root cause: _subprocess_env() in tests/system/test_scaffold_dx.py (around line 60) pops VIRTUAL_ENV, UV_PROJECT_ENVIRONMENT, COVERAGE_PROCESS_START and COVERAGE_FILE from the parent env before spawning "uv run pytest" inside the freshly rendered demo project, but does NOT pop PYTHONPATH. Any invocation of this test whose own parent process has PYTHONPATH pointed at frob's own worktree src/ (exactly what frob agent env / T-4459 exports, and what every worktree-based agent is told to eval before running pytest) leaks that PYTHONPATH into the nested "uv run pytest tests/ --cov=src --cov-report=xml" subprocess. That subprocess then resolves frob's own src/frob/__init__.py ahead of the demo project's own site-packages, which imports frob.excludes -> pathspec, a dependency the demo venv never installed, and the nested pytest run crashes with ModuleNotFoundError before it can even collect the demo project's own tests.

Effect: any agent that has done the standard eval "$(frob agent env <worktree>)" (or otherwise has PYTHONPATH pointed at a frob checkout's src/) cannot get a passing run of this test, so it cannot be bound as evidence for scaffold-template tickets from a normal agent shell -- reproduced while working T-4763.

Fix: add PYTHONPATH to the same os.environ.pop(...) block _subprocess_env() already uses for VIRTUAL_ENV/UV_PROJECT_ENVIRONMENT/COVERAGE_*.

found while working T-4763 (declared scope: shared/python/pyproject.toml.j2 and types/python-tool/**, does not include tests/system/test_scaffold_dx.py).