---
id: T-5445
title: SQL103/SQL107 + TS/Prisma N+1 ORM rules
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/sql/_orm_rules.py
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
found while working T-5337: filter-after-fetch (SQL103), server-cache-layer-for-repeated-expensive-queries (SQL107), and a TypeScript/Prisma N+1 walk (include/no-include mirrors Django's select_related) were cut from T-5337's scope to keep that leaf reviewable; SQL101/102/104/105/106 landed with real Python-first detection and migration_scan/pool-config helpers other leaves can reuse