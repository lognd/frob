---
id: T-5284
title: Re-slice open tickets into goal-named sprints (T-5133 step 3 follow-up)
state: queued
kind: feature
origin: human
created: '2026-09-22'
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
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets
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
found while working T-5133: step (3) of T-5133's body (re-slice ~600 open tickets into goal-named kebab-case sprint labels, mapped from each epic's own slug, sized to measured velocity) is data-content work across the live queue, not mechanical migration -- cut from T-5133's own scope for time. T-5133 shipped the mechanical half: validate_sprint refusal, sprint_shape_warning, and frob ticket sprint migrate (moves semver-shaped sprint values onto milestone). This ticket is the actual re-slicing pass.