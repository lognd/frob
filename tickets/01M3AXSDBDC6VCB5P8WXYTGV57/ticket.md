+++
id = "01M3AXSDBDC6VCB5P8WXYTGV57"
title = "SYSDESIGN407: container spec with no resources.requests set"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD8AD5W7ECRJX8VGNKVM"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:57Z"
aliases = ["T-6509"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_horizontal.py", "tests/fixtures/sysdesign/sysdesign407/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7TTVWH9XEP3NH163QX"
+++

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
