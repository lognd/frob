+++
id = "01M3AXSDAT3VXZC4R6BRJG2NEW"
title = "SYSDESIGN404: multi-replica Deployment with no matching PodDisruptionBudget"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8AD5W7ECRJX8VGNKVM"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6490"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_horizontal.py", "tests/fixtures/sysdesign/sysdesign404/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7TTVWH9XEP3NH163QX"
+++

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
