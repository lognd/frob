---
id: T-draft-382f12d0
title: ORM N+1 and pooling rules (Python/TS) + DB pool config, cache-layer, migration-TTL
  scan
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5148
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/sql/_orm_rules.py
- tests/fixtures/sql/**
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
AST lint for lazy-relationship access inside a loop with no joinedload/selectinload (SQLAlchemy), no select_related/prefetch_related (Django), no include (Prisma); .all() without .limit() on a request path; filter-after-fetch; missing-index cross-check against migration files' declared indexes vs ORM model FK/WHERE/ORDER columns; missing transaction wrapper around multi-statement writes; missing connection-pool config (PgBouncer/SQLAlchemy pool) and no server-cache-layer-for-repeated-expensive-queries -- this leaf is the canonical owner of DB-pool-config and the migration-schema-scan helper; T-5147-6 (WEBPERF) blocks on this leaf for pool config instead of reimplementing it, and T-5145-3 (COMPLY GDPR storage-limitation) blocks on this leaf's migration-scan helper for the PII-retention-TTL-column check instead of building a second migration parser. Fixture per rule id.