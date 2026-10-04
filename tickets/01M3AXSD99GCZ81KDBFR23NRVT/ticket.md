+++
id = "01M3AXSD99GCZ81KDBFR23NRVT"
title = "SYSDESIGN503: data store with no declared consistency model"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD8X08Y5AGX1VX1CH4QH"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:58:53Z"
aliases = ["T-6441"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_data_tier.py", "tests/fixtures/sysdesign/sysdesign503/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD9WQ0QPZJ3E2G99DAXB"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN503: data store with no declared consistency model
kind: feature
tier: leaf
parent: T-SYS-SG
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_data_tier.py, docs/modules/gates.md (SYSDESIGN503 row),
       tests/fixtures/sysdesign/sysdesign503/**
blocked_by: [T-SYS-A-INFRA-STORE]
tag: Static: design

Research row 8.9 (not independently sourced with a specific quotable line this pass; AWS/GCP
reliability pillars discuss consistency at the pillar level generally). Lint condition: "A data
store with no declared consistency model in the design file flags as underspecified for a
distributed deployment."

Reads the `consistency IDENT` store_prop clause added by T-SYS-A-INFRA-STORE. Second finding in
the same module, per STRATA-EXPRESSIVENESS.md section C "transactions scope": "a
`transaction`/`saga`-marked op (REL300/301) touching a store with `consistency eventual` is an
unproven atomicity claim across an eventually-consistent store."

Acceptance criteria: SYSDESIGN503 fires on either of two conditions, folded into one id per
the coordinator's contiguous-numbering directive -- a store with no `consistency` clause
flags; a REL300/301 transaction/saga-marked op touching a store declared `consistency
eventual` also flags. Positive-control fixture: tests/fixtures/sysdesign/sysdesign503/
store-no-consistency-declared/**.
