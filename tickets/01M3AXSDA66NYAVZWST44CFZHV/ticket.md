+++
id = "01M3AXSDA66NYAVZWST44CFZHV"
title = "SYSDESIGN405: multi-AZ-declared Deployment with no topologySpreadConstraints/podAntiAffinity"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD8AD5W7ECRJX8VGNKVM"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:24Z"
aliases = ["T-6470"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_horizontal.py", "tests/fixtures/sysdesign/sysdesign405/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7TTVWH9XEP3NH163QX"

[[links]]
kind = "blocked-by"
target = "01M3AXSD8PA5T397SA3B0CBGCY"
+++

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
