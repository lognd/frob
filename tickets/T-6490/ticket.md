---
id: T-6490
title: 'SYSDESIGN404: multi-replica Deployment with no matching PodDisruptionBudget'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6394
parent: T-6410
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
- tests/fixtures/sysdesign/sysdesign404/**
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
title: SYSDESIGN404: multi-replica Deployment with no matching PodDisruptionBudget
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN404 row),
       tests/fixtures/sysdesign/sysdesign404/**
blocked_by: [T-SYS-B-K8S]
tag: Static: config

Research row 7.4: Kubernetes PDB docs, https://kubernetes.io/docs/tasks/run-application/
configure-pdb/ -- "Decide how many instances can be down at the same time for a short period
due to a voluntary disruption. Stateless frontends: Concern: don't reduce serving capacity by
more than 10%. Solution: use PDB with minAvailable 90% for example." Lint condition:
"Deployment with `replicas >= 2` and no matching PodDisruptionBudget resource in the manifest
set flags."

Acceptance criteria: matches T-SYS-B-K8S's parsed Deployments (`replicas >= 2`) against
PodDisruptionBudget resources by label selector; flags an unmatched Deployment. Positive-
control fixture: tests/fixtures/sysdesign/sysdesign404/multi-replica-no-pdb/**.
