---
id: T-5446
title: 'sqlfluff plugin: schema/session-level performance rules split off T-5335'
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
- src/frob/sql/_sqlfluff_plugin.py
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
found while working T-5335: WHERE-vs-ON on outer joins, non-sargable predicates, NOT-IN-over-nullable-subquery, OR-across-columns, correlated-subquery-where-join-fits, DISTINCT-masking-fan-out, COUNT(*)-vs-EXISTS, no-LIMIT-on-interactive-query, missing-statement_timeout, long-transaction -- these ten candidate rules from T-5335's own body need schema/session state (index catalog, cross-statement session config, resolved query plan) beyond a single-statement sqlfluff AST plugin's reach. T-5335's own contingency clause splits them off rather than forcing the fit.