---
id: T-draft-82754308
title: 'SYSDESIGN410: at-least-once queue consumer with no dedup/idempotency check'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-3ed25d21
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
- src/frob/sysdesign/_consumers.py (new)
- tests/fixtures/sysdesign/sysdesign410/**
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
