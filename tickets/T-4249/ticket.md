---
id: T-4249
title: 'client-side totality mirror: export a server registry''s total code/field
  set and require the consumer to enumerate and handle/ignore every entry'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
blocked_by:
- T-4072
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
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
- src/frob/gates
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
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
Consumer F-327/M-1,M-5 (T-4135 sub-epic, API contract audit), consolidated with F-362/M4-5 (T-4166 -- splitting a display-only error-code list from a needs-recovery axis is the client-side half of this same totality gap). A backend's _assert_total_coverage()-style check proves every registered error has a mapping -- a claim about the registry, not the response surface as seen by the client. Nothing enumerates the codes the backend can emit and requires the consumer to enumerate and handle/ignore each. Blocked by T-4072 (generated-types staleness + hand-written-interface ban): this needs the generated contract artifact T-4072 establishes to exist before a client-side totality test can be written against it. Not fixture-testable in frob's own tree: no client/server duo exists here.