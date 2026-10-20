+++
id = "01M3AXSDAHDEJSCDMMDSECH7YK"
title = "SYSDESIGN505: production service with no declared cell/multi-region active-active/passive posture"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8X08Y5AGX1VX1CH4QH"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6481"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_data_tier.py", "tests/fixtures/sysdesign/sysdesign505/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8PA5T397SA3B0CBGCY"

[[links]]
kind = "blocked-by"
target = "01M3AXSDAJ8YB45QEY8G9Z8DWV"
+++

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
