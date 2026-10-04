+++
id = "01M35RZYA6BY9936Z3H6M7AGD4"
title = "sqlfluff plugin: schema/session-level performance rules split off T-5335"
type = "task"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5446"]
labels = ["v1-cluster:B2", "area:grimble"]
scope = ["src/frob/sql/_sqlfluff_plugin.py"]
+++

found while working T-5335: WHERE-vs-ON on outer joins, non-sargable predicates, NOT-IN-over-nullable-subquery, OR-across-columns, correlated-subquery-where-join-fits, DISTINCT-masking-fan-out, COUNT(*)-vs-EXISTS, no-LIMIT-on-interactive-query, missing-statement_timeout, long-transaction -- these ten candidate rules from T-5335's own body need schema/session state (index catalog, cross-statement session config, resolved query plan) beyond a single-statement sqlfluff AST plugin's reach. T-5335's own contingency clause splits them off rather than forcing the fit.
