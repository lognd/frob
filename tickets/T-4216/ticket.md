---
id: T-4216
title: 'strata: declare page-wide/global capabilities distinctly from component-local
  ones, with a required scoping predicate'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4157
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
Consumer F-357/H4-4 (T-4157): a component installing a window-level keydown listener is a page-wide capability, not a component-local one, and no gate models the distinction. Add a global-scope capability kind (e.g. dom.global_key_capture) whose ceiling requires a declared focus-scoping predicate; a node that captures globally without one fails SYS100. Not fixture-testable in frob's own tree: no DOM/global-listener surface exists here.