---
id: T-6394
title: Kubernetes manifest ingestion (Deployment/Service/Ingress/HPA/PDB/NetworkPolicy/probes/resources)
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6396
parent: T-6426
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
- src/frob/lang/_config_k8s.py (new)
- tests/fixtures/sysdesign/config-k8s/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1492
  new_length: 1581
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
