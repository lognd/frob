---
id: T-draft-adc8cbd1
title: 'SQL: extract SQL from host languages, sqlfluff as parser with a frob rule
  plugin for performance semantics, squawk for migrations, ORM N+1 and pooling rules,
  EXPLAIN obligation on flagged queries'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: T-draft-09897a86
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
30 entries, 23 static. Engine decision: sqlfluff (real multi-dialect parser, plugin API) for parsing and style; frob ships the performance rules sqlfluff lacks as a sqlfluff plugin: HAVING used as WHERE, WHERE vs ON placement on outer joins (semantic difference), SELECT *, non-sargable predicates (function on column, leading-wildcard LIKE, implicit casts), NOT IN over nullable subquery, OR across columns, correlated subquery where a join fits, DISTINCT masking join fan-out, COUNT(*) vs EXISTS, OFFSET pagination, no LIMIT on interactive queries, UPDATE/DELETE without WHERE, ORDER BY without supporting index and LIMIT, missing statement_timeout, long transactions. squawk as the migration-safety adapter (NOT NULL without default, index without CONCURRENTLY, lock-taking rewrites). Extraction: tree-sitter pulls SQL literals and f-string skeletons from cursor.execute, SQLAlchemy text(), Django raw(), Prisma queryRaw, sqlx macros, asyncpg/psycopg calls; any non-literal composition is the injection finding (WEBSEC) except psycopg.sql composition. ORM rules in Python/TS: N+1 from lazy relationship access inside a loop (SQLAlchemy without joinedload/selectinload, Django without select_related/prefetch_related, Prisma without include), .all() without limit on request paths, filter-after-fetch, missing index on FK/WHERE/ORDER columns cross-checked against migrations and models, missing transaction around multi-statement writes, no connection pool config. Proof: a query flagged for performance carries an EXPLAIN ANALYZE obligation before waiver. Authorities: PostgreSQL docs 7.1-7.2 and indexing chapters, MySQL and SQL Server docs, use-the-index-luke, ORM docs. Tools sqlfluff and squawk registered as relevant when SQL literals, .sql files or migrations exist (T-draft-94870246).