---
id: T-5818
title: git spawn budget of 30 s fails legitimate calls under fleet load
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
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
scope:
- src/frob/gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gitio.py
  reason: make git spawn budget configurable, default 120s, WARN over 30s with load
    average, keep hard hang ceiling
  actor: logan
  at: '2026-09-25'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
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
Under a running drain plus 5-7 agents, plain `git status`/`git diff`
spawns inside `frob` exceed the 30 s guarded-subprocess budget and the
verb fails with "a required git operation failed" (measured 2026-09-24:
T-draft-90b33f19 land, several `frob ticket scope` calls). 30 s is a
hang guard, not a load budget. Fix: raise the git spawn budget to 120 s
(config `[git] spawn_timeout_s`), log at WARNING when a call exceeds
30 s with the load average, and keep the hang guard as the hard ceiling.
Positive control: a git call stubbed to take 45 s must succeed and log
the warning.
