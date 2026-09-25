---
id: T-6458
title: 'SYSDESIGN501: read-only traffic routed to the primary write endpoint, no replica
  configured'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6396
parent: T-6429
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
- src/frob/sysdesign/_data_tier.py (new)
- tests/fixtures/sysdesign/sysdesign501/**
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
title: SYSDESIGN501: read-only traffic routed to the primary write endpoint, no replica
       configured
kind: feature
tier: leaf
parent: T-SYS-SG
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_data_tier.py (new), docs/modules/gates.md (SYSDESIGN501 row),
       tests/fixtures/sysdesign/sysdesign501/**
blocked_by: [T-SYS-B-CONFIGDOC]
tag: Static: config

Research row 8.1: AWS Well-Architected Reliability Pillar REL05-BP01 -- "For queries that only
read, read replicas can be used, which provide redundancy and the ability to scale out, not
just up. Writes can be buffered, for example in an Amazon Simple Queue Service queue, so that
write requests from customers can still be accepted even if the primary is temporarily
unavailable." Lint condition: "A service issuing only read queries (per design model traffic
classification) against the primary write endpoint (no replica endpoint configured) flags as a
missed horizontal-read-scale opportunity."

Acceptance criteria: flags a DB client config routing 100% read-only queries (per design-model
traffic classification on the calling node) to the same endpoint used for writes, with no
distinct replica endpoint configured anywhere in the resolved ConfigDoc set. Positive-control
fixture: tests/fixtures/sysdesign/sysdesign501/read-only-service-on-primary/**.
