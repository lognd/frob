+++
id = "01M3AXSD9D6VGS7NS3X1R5MECT"
title = "SYSDESIGN403: horizontally-scaled Deployment with HPA minReplicas 1 or no HPA at all"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8AD5W7ECRJX8VGNKVM"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6445"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_horizontal.py", "tests/fixtures/sysdesign/sysdesign403/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7TTVWH9XEP3NH163QX"
+++

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
