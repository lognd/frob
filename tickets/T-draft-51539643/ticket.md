---
id: T-draft-51539643
title: 'GRAMMAR: `cell` deployment-partitioning declaration with `mode active_active|active_passive`'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-49d2300b
- T-draft-62e2a780
parent: T-draft-ffda706b
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
- strata-core/src/parse/grammar_infra.rs
- docs/strata/surface.md#std-infra
- src/frob/strata/_models.py
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
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: cell deployment-partitioning declaration with mode active_active|active_passive
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 5
scope: strata-core/src/parse/grammar_infra.rs, docs/strata/surface.md#std-infra,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/infra-cell/**
blocked_by: [T-SYS-A-INFRA-CACHE-QUEUE, T-STORE-301-ATTR]

Findings (STRATA-EXPRESSIVENESS.md, sections A "COMPUTE" and F "OPERATIONS"):

cell/shard-of-deployment -- "there is no 'this whole deployment is partitioned into N
independently-failing cells, and a customer/tenant is pinned to exactly one' construct...
Proposal (GRAMMAR): a new top-level `cell ID { residences {A, B}; }` declaration
cross-referenced by node `residence`, lives in a new grammar_infra.rs production (cell block)...
RULE-ONLY companion: 'every node with `critical` inbound flow must declare `residence` bound to
a cell' (extends REL250-style SPOF logic to cell-level blast radius). Authority: AWS cell-based
architecture whitepaper / Azure deployment stamps."

multi-AZ/multi-region active-active/passive -- "NOT EXPRESSIBLE as named strategies... This is
the SAME underlying gap as 'cell/shard-of-deployment'... recommend the SAME cell/residences
GRAMMAR proposal serve both (a cell with 2+ residences and a routing policy IS multi-region
active-active/passive, differentiated by whether all residences receive live traffic -- add
`cell_prop := mode (active_active | active_passive)`)."

Acceptance criteria: `cell ID { residences {...}; mode active_active|active_passive; }` lands
as a new grammar_infra.rs production, referenced by node `residence`. RULE-ONLY companion (a
new REL250-adjacent rule requiring `critical`-reachable nodes to declare a cell-bound
`residence`) is filed separately in Story G (SYSDESIGN505), not implemented here. Positive-
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
control fixture: tests/fixtures/sysdesign/infra-cell/critical-node-no-cell/design.strata.
