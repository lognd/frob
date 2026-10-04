+++
id = "01M3AXSD7M5PEVKRH6277ZBPRY"
title = "SYSDESIGN504: critical-reachable store with declared RPO but no declared RTO"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD8X08Y5AGX1VX1CH4QH"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:57:32Z"
aliases = ["T-6388"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_data_tier.py", "tests/fixtures/sysdesign/sysdesign504/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD9WQ0QPZJ3E2G99DAXB"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN505: critical-reachable store with declared RPO but no declared RTO
kind: feature
tier: leaf
parent: T-SYS-SG
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_data_tier.py, docs/modules/gates.md (SYSDESIGN505 row),
       tests/fixtures/sysdesign/sysdesign505/**
blocked_by: [T-SYS-A-INFRA-STORE]
tag: Static: design

Research row 9.7 (AWS pillar fetched at intro level; RPO/RTO-specific DR sub-page not
independently fetched this pass, flagged in-row as a gap). Finding
(STRATA-EXPRESSIVENESS.md, section C): "RPO is COVERED, RTO is NONE... Proposal (GRAMMAR):
store_prop `rto QUANTITY`, same shape as `rpo`... Enables RULE: a `critical`-reachable store
with `rpo` but no `rto` is half a DR story (mirrors the existing detect/revoke-both-mandatory
pattern in BreachContract). Authority: ISO 22301 / AWS Well-Architected Reliability Pillar
RPO/RTO pairing."

Acceptance criteria: reads the `rto QUANTITY` store_prop clause added by T-SYS-A-INFRA-STORE;
flags a store reachable via an inbound `critical` flow (same reachability test REL250 SPOF
already runs) that declares `rpo` but not `rto`. Positive-control fixture: tests/fixtures/
sysdesign/sysdesign505/critical-store-rpo-no-rto/**.
