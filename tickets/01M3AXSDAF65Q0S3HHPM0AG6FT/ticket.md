+++
id = "01M3AXSDAF65Q0S3HHPM0AG6FT"
title = "SYSDESIGN408: (pool_size_per_replica * max_replicas) exceeds declared DB max_connections"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8AD5W7ECRJX8VGNKVM"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6479"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_horizontal.py", "tests/fixtures/sysdesign/sysdesign408/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD9WQ0QPZJ3E2G99DAXB"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN409: (pool_size_per_replica * max_replicas) exceeds declared DB max_connections
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN409 row),
       tests/fixtures/sysdesign/sysdesign409/**
blocked_by: [T-SYS-A-INFRA-STORE]
tag: Static: design

Research row 7.9 (not independently sourced with a direct "pool size x replicas <= max
connections" quote this pass; AWS REL05-BP06 stateless/offload guidance cited contextually).
Lint condition: "(pool_size_per_replica * max_replicas) > declared DB max_connections flags a
scale-out-triggered connection exhaustion risk."

Acceptance criteria: reads the app's DB-client pool-size config, the design model's
`capacity replicas N..M`, and the target store's declared connection limit (or a
config-declared `max_connections`); flags when the arithmetic product exceeds the limit.
Positive-control fixture: tests/fixtures/sysdesign/sysdesign409/pool-times-replicas-exceeds-
max-connections/**.
