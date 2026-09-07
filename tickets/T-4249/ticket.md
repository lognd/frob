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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
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
Consumer F-327/M-1,M-5 (T-4135 sub-epic, API contract audit), consolidated with F-362/M4-5 (T-4166 -- splitting a display-only error-code list from a needs-recovery axis is the client-side half of this same totality gap). A backend's _assert_total_coverage()-style check proves every registered error has a mapping -- a claim about the registry, not the response surface as seen by the client. Nothing enumerates the codes the backend can emit and requires the consumer to enumerate and handle/ignore each. Blocked by T-4072 (generated-types staleness + hand-written-interface ban): this needs the generated contract artifact T-4072 establishes to exist before a client-side totality test can be written against it. Not fixture-testable in frob's own tree: no client/server duo exists here.