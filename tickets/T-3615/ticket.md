---
id: T-3615
title: 'guard hooks: pass --help/--version and read-only verbs, never lexically match
  command content'
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: high
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
