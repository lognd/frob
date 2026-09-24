---
id: T-5472
title: 'app_runners JSON guard: runner produces empty stdout instead of JSON'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
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
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/test_app_runners_json_guard_t2492.py::TestFmtRunnerJsonGuard::test_planted_leak_does_not_reach_stdout

The test captures a runner's stdout and expects valid JSON; it gets an
EMPTY string instead (json.decoder.JSONDecodeError: Expecting value: line
1 column 1 char 0) -- the runner produced no JSON output at all where the
test's own positive control (T-2492's planted-leak guard) expects some.

Needs: identify which runner under test stopped emitting JSON (or started
emitting nothing) and why. Not narrowed further in this drain pass; this
file is in touch-scope (not webapp/sql/strata-core).
