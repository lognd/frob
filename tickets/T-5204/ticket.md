---
id: T-5204
title: 'frob doctor: report lint-tool version lag against latest PyPI/npm/crates release'
state: in-progress
kind: feature
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_doctor.py::TestLintToolVersionLag::test_stale_tool_is_a_finding
- tests/unit/test_doctor.py::TestLintToolVersionLag::test_fresh_tool_is_not_a_finding
- tests/unit/test_doctor.py::TestLintToolVersionLag::test_missing_tool_is_skipped
- tests/unit/test_doctor.py::TestLintToolVersionLag::test_fetch_false_serves_only_from_cache
- tests/unit/test_doctor.py::TestLintToolVersionLag::test_fresh_cache_entry_skips_the_network
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5204
branch: t-5204
---
T-5138 acceptance [5] (given ruff two minor versions behind PyPI, frob doctor reports the lag) is out of T-5138's declared scope (src/frob/vet/*.py, frob.toml, docs/modules/vet.md, src/frob/strata/_cve_fingerprint.py -- doctor.py is not in it). DESIGN item 7 from T-5138: frob doctor reports installed ruff/ty/mypy/eslint/clippy versions against the latest PyPI/npm/crates release, cached 24h, warns past a configurable lag.