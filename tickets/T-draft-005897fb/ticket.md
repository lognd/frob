---
id: T-draft-005897fb
title: 'SYSDESIGN504: critical-reachable store with declared RPO but no declared RTO'
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
- tests/fixtures/sysdesign/sysdesign504/**
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
