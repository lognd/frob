---
id: T-5335
title: sqlfluff integration + frob performance-rule plugin + REQUIRED-for-family tool
  gating
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
- src/frob/sql/_sqlfluff_plugin.py
- src/frob/doctor.py
- pyproject.toml
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
sqlfluff plugin (sqlfluff.rules entry-point group) hosting frob's own performance rules: HAVING-as-WHERE, WHERE-vs-ON on outer joins, SELECT *, non-sargable predicates, NOT-IN-over-nullable-subquery, OR-across-columns, correlated-subquery-where-join-fits, DISTINCT-masking-fan-out, COUNT(*)-vs-EXISTS, OFFSET-pagination, no-LIMIT-on-interactive-query, UPDATE/DELETE-without-WHERE, ORDER-BY-without-index-and-LIMIT, missing-statement_timeout, long-transaction. If more than ~half of these don't fit sqlfluff's plugin rule-class cleanly, split the session/config-level ones (UPDATE/DELETE-without-WHERE, missing-statement_timeout, long-transaction) into a follow-up ticket rather than forcing the fit. OWNER DIRECTIVE: sqlfluff is REQUIRED FOR THE SQL FAMILY, not OPTIONAL_FOR_GATE -- add a NEW tool-category shade in src/frob/doctor.py (ToolCategory currently has REQUIRED/OPTIONAL/OPTIONAL_FOR_GATE; this needs a fourth: relevant_when = 5148-1's SQL-relevance predicate (a .sql file or SQL-executing call site exists); when relevant, absence is a FAILING UNMEASURED verdict for the whole SQL family, not a gate-level advisory; when no SQL exists anywhere in the repo, sqlfluff is never demanded at all. Wire the pyproject.toml dependency + plugin registration in this leaf too.