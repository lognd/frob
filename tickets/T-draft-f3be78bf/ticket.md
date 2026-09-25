---
id: T-draft-f3be78bf
title: 'SYSDESIGN407: container spec with no resources.requests set'
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
- tests/fixtures/sysdesign/sysdesign407/**
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
title: SYSDESIGN408: container spec with no resources.requests set
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 1
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN408 row),
       tests/fixtures/sysdesign/sysdesign408/**
blocked_by: [T-SYS-B-K8S]
tag: Static: config

Research row 7.8: Kubernetes resource management docs, https://kubernetes.io/docs/concepts/
configuration/manage-resources-containers/ -- "For each container, you can specify resource
limits and requests... memory limits are enforced by the kernel with out of memory (OOM)
kills." Lint condition: "Container spec with no `resources.requests` set flags (scheduler
cannot bin-pack correctly, undermining horizontal scaling economics)."

Cross-reference: the OS-process analog (REL392/393 `cgroup_bounds`) already covers non-k8s
deployment; this rule is the k8s-manifest-literal check the inventory confirms is missing
("PARTIAL. REL392/393 cover cgroup_bounds on a deployed_process node... but there is no
k8s-manifest-literal (requests.cpu/limits.memory) check").

Acceptance criteria: flags a T-SYS-B-K8S container spec with no `resources.requests.cpu` and no
`resources.requests.memory`. Positive-control fixture: tests/fixtures/sysdesign/sysdesign408/
container-no-requests/**.
