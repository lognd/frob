---
id: T-6481
title: 'SYSDESIGN505: production service with no declared cell/multi-region active-active/passive
  posture'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6422
- T-6482
parent: T-6429
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
- src/frob/sysdesign/_data_tier.py
- tests/fixtures/sysdesign/sysdesign505/**
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
title: SYSDESIGN506: production service with no declared cell/multi-region active-active/
       passive posture
kind: feature
tier: leaf
parent: T-SYS-SG
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_data_tier.py, docs/modules/gates.md (SYSDESIGN506 row),
       tests/fixtures/sysdesign/sysdesign506/**
blocked_by: [T-SYS-A-INFRA-CELL, T-SYS-H-RESEARCH-GAPS]
tag: Static: design

Research row 9.7: "A service declared 'production' with no RPO/RTO entry in the design model
flags" -- the multi-region-posture half of this row (as distinct from the RPO/RTO-per-store
half filed as SYSDESIGN505) reads T-SYS-A-INFRA-CELL's `cell { residences {...}; mode
active_active|active_passive; }` declaration. Filed blocked_by T-SYS-H-RESEARCH-GAPS since the
RPO/RTO DR sub-page citation for this row was not independently fetched.

Acceptance criteria: flags a node declared "production" (per the same convention SYSDESIGN
REL280/281 SLO checks use) with no `cell` reference at all, i.e. no declared multi-region
posture one way or the other. Positive-control fixture: tests/fixtures/sysdesign/sysdesign506/
production-service-no-cell/**.
