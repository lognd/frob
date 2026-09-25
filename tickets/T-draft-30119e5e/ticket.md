---
id: T-draft-30119e5e
title: 'SYSDESIGN106: default-allow security group / broad ingress on data tier /
  public subnet for data resource'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-4a00f41a
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
- src/frob/sysdesign/_segmentation.py (new)
- tests/fixtures/sysdesign/sysdesign106/**
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
title: SYSDESIGN106: default-allow security group / broad data-tier ingress / public subnet
       for a data resource
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_segmentation.py (new), docs/modules/gates.md (SYSDESIGN106 row),
       tests/fixtures/sysdesign/sysdesign106/**
blocked_by: [T-SYS-B-TERRAFORM, T-SYS-H-RESEARCH-GAPS]
tag: Static: config

Research rows 4.1-4.4 (NIST SP 800-41 citation gap noted explicitly in-row; "Citation retained
[by title + publication number] but NOT independently quoted -- flagged in Coverage
checklist"). Lint conditions combined into one rule family: 4.1 "Security group with a default
`allow all` egress or ingress rule (no explicit allow-list) flags"; 4.2 "Data-tier resource
(RDS/database) with a security group allowing ingress from a CIDR broader than the app tier's
SG flags"; 4.3 "Database/cache resource provisioned in a subnet with a default route
(`0.0.0.0/0`) to an internet gateway flags"; 4.4 "Security group / NACL with unrestricted
(`0.0.0.0/0` all ports) egress on a data-tier or restricted-tier resource flags." Filed
blocked_by T-SYS-H-RESEARCH-GAPS pending the NIST 800-41 PDF text fetch.

Acceptance criteria: four findings functions in one module reading T-SYS-B-TERRAFORM's
`aws_security_group`/`aws_subnet`/`aws_route_table` resources for: (a) default-allow ingress/
egress, (b) data-tier SG ingress CIDR broader than app-tier SG, (c) data resource in a subnet
with a default internet-gateway route, (d) unrestricted egress on a data/restricted-tier
resource. Positive-control fixtures: tests/fixtures/sysdesign/sysdesign106/{default-allow-sg,
broad-data-tier-ingress,public-subnet-db,unrestricted-egress}/**.
