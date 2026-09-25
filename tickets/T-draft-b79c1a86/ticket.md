---
id: T-draft-b79c1a86
title: 'STORE202: `*_cache`-named table with no expiry column (relational)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-8980afab
tier: ticket
sprint: store-family
runs_last: false
milestone: 0.538.0
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
- src/frob/store/_relational.py
- tests/fixtures/store/store202-relational-cache-table-no-ttl/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE202.

Authority: same family as STORE119/DB-as-cache; Postgres offers no
built-in TTL/eviction primitive, unlike Redis's `EXPIRE` (STORE103's own
authority) -- the absence of the feature is itself the signal, per the
research file's own framing.

Call shapes: table/model literally named `cache`/`*_cache` with
`created_at` but no expiry column, or app code manually `DELETE FROM
cache WHERE created_at < now() - interval`.

Repo fact needed: schema/migration column list for a table matching the
`*cache*` name heuristic (reuse `migration_scan`).

Positive-control fixture:
`tests/fixtures/store/store202-relational-cache-table-no-ttl/`.

Relevance gate: relational SQL surface detected.
