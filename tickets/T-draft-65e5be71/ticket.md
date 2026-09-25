---
id: T-draft-65e5be71
title: 'SYSDESIGN103: upstream cluster with neither active health check nor outlier
  detection'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-56ac0a37
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
- src/frob/sysdesign/_lb.py (new)
- tests/fixtures/sysdesign/sysdesign103/**
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
