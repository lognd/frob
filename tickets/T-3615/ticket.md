---
id: T-3615
title: 'guard hooks: pass --help/--version and read-only verbs, never lexically match
  command content'
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: medium
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks
- tests/unit/test_hooks_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks
  reason: hook fixes live in the repo copies of the hooks
  actor: logan
  at: '2026-09-15'
- op: add
  glob: tests/unit/test_hooks_guard.py
  reason: hook fixes live in the repo copies of the hooks
  actor: logan
  at: '2026-09-15'
triage_changes:
- field: priority
  old_value: high
  new_value: medium
  reason: 'T-4483 follow-up: TICK004 escalated to error on 2026-09-15 (15d queued
    > 2x the 7d high threshold) and reds every CI leg; these are T-3611 latency-epic
    children, sprint v0.532.0 work behind the v0.531.0 alpha cut, not alpha-path work,
    so medium is the honest priority'
  actor: logan
  at: '2026-09-14'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Three measured guard false-positives (see epic body): the root-write
guard and the frob-timeout-guard hooks match verb SHAPES and command
CONTENT lexically. Fix in the hooks (.claude/hooks/*, edit the REPO
copies, sync after): (a) any invocation whose argv contains
--help/--version, or whose verb is a documented read-only verb, passes
unconditionally regardless of cwd; (b) never scan heredoc/quoted string
CONTENT for verb phrases -- tokenize the actual command position
(shlex), fleet doctrine: token/grammar fixes, never lexical; (c) the
timeout-guard exempts --help/--version forms. Tests in the hook suites
for each: help-from-root passes, real land from root still refused,
heredoc containing verb phrases writing OUTSIDE the repo passes.
