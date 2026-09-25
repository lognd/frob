---
id: T-draft-4d01dafa
title: 'SYSDESIGN104: LB deregistration_delay unset while workload terminationGracePeriodSeconds
  is shorter'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-0e74c702
parent: T-draft-56ac0a37
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
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
- src/frob/sysdesign/_lb.py
- tests/fixtures/sysdesign/sysdesign104/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN104: LB deregistration_delay unset while workload terminationGracePeriodSeconds
       is shorter, a request-drop race
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_lb.py, docs/modules/gates.md (SYSDESIGN104 row),
       tests/fixtures/sysdesign/sysdesign104/**
blocked_by: [T-SYS-B-K8S, T-SYS-B-TERRAFORM]
tag: Static: config

Research row 2.5 (citation partial -- AWS pillar fetched at intro level only, sub-page 404'd):
evidence artifact "ALB/NLB target-group `deregistration_delay.timeout_seconds`, or k8s
`terminationGracePeriodSeconds` combined with readiness-gate removal." Lint condition: "Target
group / Service with `deregistration_delay` unset (defaulting) while
`terminationGracePeriodSeconds` on the workload is shorter than the LB drain window flags a
request-drop race."

Acceptance criteria: cross-references T-SYS-B-TERRAFORM's `aws_lb_target_group.
deregistration_delay` against T-SYS-B-K8S's matching Deployment's
`spec.template.spec.terminationGracePeriodSeconds`; flags when the grace period is shorter than
the drain window (or the drain window is unset/defaulting). Positive-control fixture:
tests/fixtures/sysdesign/sysdesign104/short-grace-period/**.
