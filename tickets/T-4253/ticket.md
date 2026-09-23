---
id: T-4253
title: 'strata: connect a browser node''s declared media/fetch capability grants to
  the CSP/edge policy that permits or denies them at runtime'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4182
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
- src/frob/strata
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
Consumer F-386 item 2 (T-4182, shell round-5): a CSP is a string in an edge-server config snippet; frob check has no gate that reads it, and frob sys audit reasons about code capabilities (may fetch_url grants) not the edge policy that would permit or deny them at runtime -- nothing connects a browser node's declared media loads to the header that actually governs them. Not fixture-testable in frob's own tree: no CSP/edge-policy config exists here.