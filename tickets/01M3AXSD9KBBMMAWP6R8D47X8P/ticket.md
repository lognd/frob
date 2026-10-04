+++
id = "01M3AXSD9KBBMMAWP6R8D47X8P"
title = "SYSDESIGN410: at-least-once queue consumer with no dedup/idempotency check"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8AD5W7ECRJX8VGNKVM"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6451"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_consumers.py (new)", "tests/fixtures/sysdesign/sysdesign410/**"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN411: at-least-once queue consumer with no dedup/idempotency check
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_consumers.py (new), docs/modules/gates.md (SYSDESIGN411 row),
       tests/fixtures/sysdesign/sysdesign411/**
blocked_by: []
tag: Static: code

Research row 7.11: Stripe Engineering, "Designing robust and predictable APIs with
idempotency", https://stripe.com/blog/idempotency -- "The easiest way to address
inconsistencies in distributed state caused by failures is to implement server endpoints so
that they're idempotent... When a client sees any kind of error, it can ensure the convergence
of its own state with the server's by retrying." (applied here to queue consumers under
at-least-once delivery, per the same idempotency-key mechanism). Lint condition: "A queue
consumer with no deduplication/idempotency check, consuming from a queue whose design model
declares 'at-least-once' delivery, flags."

Distinct from REL221 (retry-path idempotency on the SENDING side, existing): this rule is the
CONSUMING side of a `delivery=at_least_once` queue (REL330/331 already proves delivery
semantics are declared; this rule proves the consumer actually dedupes against redelivery).

Acceptance criteria: flags a consumer function bound to a `queue` node with `delivery
at_least_once` that has no message-ID/idempotency-key dedup check before applying a side
effect. Positive-control fixture: tests/fixtures/sysdesign/sysdesign411/
at-least-once-consumer-no-dedup/**.
