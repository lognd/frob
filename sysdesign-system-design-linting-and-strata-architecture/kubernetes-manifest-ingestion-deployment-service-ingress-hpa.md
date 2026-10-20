+++
id = "01M3AXSD7TTVWH9XEP3NH163QX"
title = "Kubernetes manifest ingestion (Deployment/Service/Ingress/HPA/PDB/NetworkPolicy/probes/resources)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8TNZP3PQVKB7EKCR7M"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6394"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/lang/_config_k8s.py (new)", "tests/fixtures/sysdesign/config-k8s/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7WN9GJ27A1ZEMT1JYG"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: Kubernetes manifest ingestion (Deployment/Service/Ingress/HPA/PDB/NetworkPolicy/
       probes/resources)
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 5
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_k8s.py (new), docs/modules/lang.md,
       tests/fixtures/sysdesign/config-k8s/**
blocked_by: [T-SYS-B-CONFIGDOC]

Body:

frob's only existing Kubernetes-YAML capability is EXPORT direction (`frob.strata._export.
export_k8s_netpol` generates a NetworkPolicy skeleton FROM a design model); it does not ingest
existing cluster YAML (SYSDESIGN-INVENTORY.md sec 2). This leaf is the INGEST direction the
Story F horizontal-readiness rules (HPA, PDB, probes, resource requests/limits, topology
spread) and Story C edge rules (Ingress TLS annotation) are blocked_by.

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Acceptance criteria: `frob.lang._config_k8s.parse(path) -> list[ConfigDoc]` covers `kind:
Deployment|Service|Ingress|HorizontalPodAutoscaler|PodDisruptionBudget|NetworkPolicy` at
minimum, exposing `spec.template.spec.containers[].readinessProbe/livenessProbe/startupProbe/
resources`, `spec.minReplicas`, `spec.minAvailable`, `spec.rules` (Ingress). Positive-control
fixture: tests/fixtures/sysdesign/config-k8s/full-manifest-set/** with one manifest per kind.
