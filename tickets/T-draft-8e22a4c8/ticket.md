---
id: T-draft-8e22a4c8
title: Wire dotnet/unity test runners into ticket-runner CLI for csharp/Unity node
  ids
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
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
- src/frob/app/ticket_runner/**
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
T-4516's own scope note (WIRE001 waiver on run_dotnet_tests/run_unity_batchmode) said this routing was T-4516's job, but T-4516 closed as a story rollup without actually wiring the CLI: no src/frob/app/** caller of run_dotnet_tests/run_unity_batchmode exists. Route frob's ticket-runner CLI to call these for csharp/Unity node ids (blocked on T-4518's project-model detection, same as the original note). Found while working T-5470.