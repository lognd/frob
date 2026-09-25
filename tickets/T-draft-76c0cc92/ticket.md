---
id: T-draft-76c0cc92
title: 'SYSDESIGN403: horizontally-scaled Deployment with HPA minReplicas 1 or no
  HPA at all'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-0e74c702
parent: T-draft-3ed25d21
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
- src/frob/sysdesign/_horizontal.py
- tests/fixtures/sysdesign/sysdesign403/**
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
title: SYSDESIGN403: horizontally-scaled Deployment with HPA minReplicas 1 or no HPA at all
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 1
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN403 row),
       tests/fixtures/sysdesign/sysdesign403/**
blocked_by: [T-SYS-B-K8S]
tag: Static: config

Research row 7.3: Kubernetes HPA docs, https://kubernetes.io/docs/tasks/run-application/
horizontal-pod-autoscale/ (fetched; documents `spec.minReplicas`, separately notes "For
HorizontalPodAutoscalers that scale on custom (object) or external metrics, you can set
spec.minReplicas to 0"). Lint condition: "Deployment declared 'horizontally scaled' in the
design model with HPA `minReplicas` set to 1 (or Deployment `replicas: 1` and no HPA at all)
flags."

Acceptance criteria: reads T-SYS-B-K8S's parsed HPA `spec.minReplicas` (or Deployment
`spec.replicas` when no HPA references it); flags 1 or absence for a workload the strata design
model declares `capacity replicas N..M` with N or M > 1 (i.e. declared horizontally scaled).
Positive-control fixture: tests/fixtures/sysdesign/sysdesign403/hpa-min-replicas-1/**.
