---
id: T-draft-9b722523
title: 'SYSDESIGN405: multi-AZ-declared Deployment with no topologySpreadConstraints/podAntiAffinity'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
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
- tests/fixtures/sysdesign/sysdesign405/**
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
title: SYSDESIGN405: multi-AZ-declared Deployment with no topologySpreadConstraints/
       podAntiAffinity
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN405 row),
       tests/fixtures/sysdesign/sysdesign405/**
blocked_by: [T-SYS-B-K8S, T-SYS-A-INFRA-CELL]
tag: Static: config

Research row 7.5: Kubernetes topology spread docs, https://kubernetes.io/docs/concepts/
scheduling-eviction/topology-spread-constraints/ -- "Pods are spread across your cluster among
failure-domains such as regions, zones, nodes, and other user-defined topology domains. This
can help to achieve high availability as well as efficient resource utilization." Lint
condition: "Deployment marked 'multi-AZ' in the design model with no
`topologySpreadConstraints` (or equivalent podAntiAffinity) on zone topology flags."

Cross-reference: "multi-AZ" in the design model is expressed via T-SYS-A-INFRA-CELL's `cell`
declaration with 2+ `residences` (per STRATA-EXPRESSIVENESS.md section F, "the SAME underlying
gap as cell/shard-of-deployment" note), so this rule's "declared multi-AZ" signal reads a
`cell` with 2+ residences rather than inventing a separate design-model flag.

Acceptance criteria: flags a T-SYS-B-K8S Deployment with no `topologySpreadConstraints`
(`topologyKey: topology.kubernetes.io/zone`) when the corresponding strata node's cell
declares 2+ residences. Positive-control fixture: tests/fixtures/sysdesign/sysdesign405/
multi-az-no-topology-spread/**.
