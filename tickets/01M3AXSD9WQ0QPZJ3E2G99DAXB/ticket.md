+++
id = "01M3AXSD9WQ0QPZJ3E2G99DAXB"
title = "GRAMMAR: store_prop scaling/data axis (`conflict`, `keyed_by`+`shards`, `consistency`, `retention`, `rto`, `encrypted_at_rest`)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDBEQGV8V5VHYGXBEQTV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:19Z"
aliases = ["T-6460"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["strata-core/src/parse/grammar_infra.rs", "docs/strata/surface.md#std-infra", "src/frob/strata/_models.py", "docs/design/grmb-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD926S7M96AQB9BTK4E2"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: store_prop scaling/data axis (conflict, keyed_by+shards, consistency,
       retention, rto, encrypted_at_rest)
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 5
scope: strata-core/src/parse/grammar_infra.rs, docs/strata/surface.md#std-infra,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/infra-store/**
blocked_by: [T-STORE-301-ATTR]

Findings (STRATA-EXPRESSIVENESS.md, section C "DATA"):

replication conflict -- "Multi-leader conflict resolution semantics (last-write-wins, CRDT,
vector clocks) is NOT EXPRESSIBLE -- no token addresses write-write conflict policy on a
store. Proposal (GRAMMAR): store_prop `conflict IDENT` (lww|crdt|vector_clock|manual)...
authority: Kleppmann DDIA ch.5 replication, Riak/Cassandra conflict-resolution docs."

sharding/partition key -- "`keyed_by IDENT` exists on `cache`... but NOT on `store`...
Proposal (GRAMMAR): add `keyed_by IDENT` and `shards INT` to store_prop... `shards` as typed
field (arithmetic: per-shard capacity math)... authority: DDIA ch.6 partitioning, DynamoDB
partition-key hot-key guidance."

consistency level -- "No token... Proposal (GRAMMAR): store_prop `consistency IDENT`
(strong|eventual|bounded_staleness|read_your_writes|causal)... closed vocabulary validated at
elaboration, same discipline as `access` mode... authority: Kleppmann DDIA ch.9, AWS DynamoDB/
Cosmos DB consistency-level docs."

retention -- "NOT EXPRESSIBLE -- no token. Proposal (GRAMMAR): store_prop `retention
QUANTITY`... typed field (feeds a future compliance-window rule)... authority: GDPR Art.
5(1)(e) storage limitation."

RTO -- "rpo exists, RTO -- how long recovery itself takes -- does not. Proposal (GRAMMAR):
store_prop `rto QUANTITY`, same shape as `rpo`... authority: ISO 22301 / AWS Well-Architected
Reliability Pillar RPO/RTO pairing."

encryption at rest -- "no store-at-rest encryption clause. Proposal (GRAMMAR):
`encrypted_at_rest [via IDENT]`... authority: PCI-DSS req 3.4, NIST SP 800-111."

Acceptance criteria: all six clauses land in one grammar_infra.rs change to store_prop;
`shards` is a typed field, the rest desugar to attrs registered in T-STORE-301-ATTR's table.
Positive-control fixture: tests/fixtures/sysdesign/infra-store/multi-writer-no-conflict/
design.strata.
