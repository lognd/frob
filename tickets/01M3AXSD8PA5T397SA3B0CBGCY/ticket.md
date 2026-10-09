+++
id = "01M3AXSD8PA5T397SA3B0CBGCY"
title = "GRAMMAR: `cell` deployment-partitioning declaration with `mode active_active|active_passive`"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDBEQGV8V5VHYGXBEQTV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:13Z"
aliases = ["T-6422"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["strata-core/src/parse/grammar_infra.rs", "docs/strata/surface.md#std-infra", "src/frob/strata/_models.py", "docs/design/grmb-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8GJ5GX7CMF943DYKWJ"

[[links]]
kind = "blocked-by"
target = "01M3AXSD926S7M96AQB9BTK4E2"
+++

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
