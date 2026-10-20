+++
id = "01M3AXSD8DZ00FF6VS1FFP9JWP"
title = "SYSDESIGN504: `outbox_for`-marked store with no relay flow to its queue within N hops"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8X08Y5AGX1VX1CH4QH"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6413"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_data_tier.py", "tests/fixtures/sysdesign/sysdesign504/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD926S7M96AQB9BTK4E2"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN504: outbox_for-marked store with no relay flow to its queue within N hops, or
       a dual-write with no transaction/outbox marker at all
kind: feature
tier: leaf
parent: T-SYS-SG
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_data_tier.py, docs/modules/gates.md (SYSDESIGN504 row),
       tests/fixtures/sysdesign/sysdesign504/**
blocked_by: [T-STORE-301-ATTR]
tag: Static: code / Static: design

Research row 8.6: Azure Architecture Center, "Implement the Transactional Outbox Pattern by
Using Azure Cosmos DB", https://learn.microsoft.com/en-us/azure/architecture/databases/guide/
transactional-outbox-cosmos -- "Implementing reliable messaging in distributed systems can be
challenging. This article describes how to use the Transactional Outbox Pattern for reliable
messaging and guaranteed delivery of events, which is an important part of supporting
idempotent message processing." Lint condition: "Code that performs a DB write and then
directly publishes to a message broker in two separate, non-transactional steps (dual-write)
flags."

Finding (STRATA-EXPRESSIVENESS.md, section B "outbox pattern"): "NOT EXPRESSIBLE distinctly...
Proposal (RULE-ONLY): a store attr `outbox_for=<queue-id>` (desugars via existing `attr`
clause, zero grammar change) plus a new rule: 'a node writing to both a store and a queue in
one op with no `transaction` attr AND no `outbox_for`-marked intermediate store is REL300 as
today; a store marked outbox_for a queue with no relay flow to that queue within N hops is an
incomplete outbox.' Authority: microservices.io outbox pattern / Debezium CDC-outbox writeup."

Acceptance criteria: `outbox_for=<queue-id>` attr registers in T-STORE-301-ATTR's table (no
grammar change, reuses the generic `attr` clause). Flags a store declaring `outbox_for` with no
relay flow reaching that queue within N graph hops. An op writing to both a store and a queue
directly with neither `transaction`/`saga` nor an `outbox_for`-marked intermediate store
continues to be caught by the existing REL300 (not re-filed). Positive-control fixture:
tests/fixtures/sysdesign/sysdesign504/outbox-marked-no-relay-flow/**.
