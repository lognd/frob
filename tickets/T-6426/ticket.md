---
id: T-6426
title: config-surface ingestion
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6476
tier: story
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: config-surface ingestion
kind: feature
tier: story
parent: T-SYS-EPIC
milestone: 0.539.0
sprint: sysdesign
scope: (none -- story, no direct code scope)
blocked_by: []

Body:

frob today parses zero of the config surfaces the research catalogue's evidence-artifact
column names as the check target: Kubernetes manifests, Helm values, Terraform/HCL,
docker-compose, and Envoy/NGINX/Caddy config are either not found at all or line-regex-scanned
for one narrow WEBSEC purpose (see SYSDESIGN-INVENTORY.md sec 2 "CONFIG SURFACES FROB PARSES
TODAY"). Every rule leaf in Stories C-G tagged "Static: config" is blocked_by the parser leaf
for its surface. One shared leaf (T-SYS-B-CONFIGDOC) lands first: a `ConfigDoc` contract in
frob.lang that every per-surface parser below implements, so SYSDESIGN rules read one uniform
shape regardless of which YAML/HCL/conf dialect produced it -- mirrors the existing
`frob.lang.raw_tree` precedent the STORE family reuses (DB-STORE-TREE.md) rather than inventing
a parallel per-surface API.
