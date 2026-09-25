---
id: T-draft-6fd51e60
title: 'SYSDESIGN503: data store with no declared consistency model'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-8fff1b13
parent: T-draft-5b688be5
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
- tests/fixtures/sysdesign/sysdesign503/**
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
