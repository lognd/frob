---
id: T-3811
title: add tzdata dependency for win32 (hypothesis tz-aware datetime strategy)
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml uv.lock
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
tests/test_fuzz.py::TestRunFuzz::test_ungeneratable_target_reports_no_generator fails on win32: hypothesis's datetime/timezone strategies need the tzdata package on Windows (stdlib zoneinfo has no bundled tz database there, unlike Linux/macOS which use the system tz db). Add 'tzdata; sys_platform == "win32"' to pyproject.toml dependencies and run uv lock. Part of win32 CI drain.

## Failure log
- 2026-09-08 attempt 1: Owning agent died; worktree untouched for hours and 249 files stale vs main. Work preserved: the entire change is one dependency line plus its comment, adding tzdata for sys_platform == win32 to pyproject.toml dependencies (patch at scratchpad/t3811.patch; it does NOT apply cleanly to current main, git apply --3way reports conflicts, so re-apply by hand). Requeued to release the lease on pyproject.toml, which the alpha version bump needs. Windows is advisory so this is not release-blocking.
