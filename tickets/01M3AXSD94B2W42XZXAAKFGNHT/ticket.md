+++
id = "01M3AXSD94B2W42XZXAAKFGNHT"
title = "SYSDESIGN103: upstream cluster with neither active health check nor outlier detection"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6436"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_lb.py (new)", "tests/fixtures/sysdesign/sysdesign103/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSDB73R2KVGH468Z79R41"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN103: upstream cluster with neither active health check nor outlier detection
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_lb.py (new), docs/modules/gates.md (SYSDESIGN103 row),
       tests/fixtures/sysdesign/sysdesign103/**
blocked_by: [T-SYS-B-PROXY]
tag: Static: config

Research rows 2.1/2.2: Envoy outlier detection docs, https://www.envoyproxy.io/docs/envoy/
latest/intro/arch_overview/upstream/outlier -- "Outlier detection and ejection is the process
of dynamically determining whether some number of hosts in an upstream cluster are performing
unlike the others and removing them from the healthy load balancing set... Passive and active
health checking can be enabled together or independently, and form the basis for an overall
upstream health checking solution." Lint condition: "Upstream cluster/target-group config with
neither an active health check nor outlier-detection (passive) config flags."

Acceptance criteria: reads T-SYS-B-PROXY's parsed Envoy `clusters[]` (or equivalent LB
target-group) and flags a cluster with no `health_checks` block AND no `outlier_detection`
block. Positive-control fixture: tests/fixtures/sysdesign/sysdesign103/cluster-no-checks/**.
