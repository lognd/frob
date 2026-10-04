+++
id = "01M336K76V7NQ9PPJ6XWQQFCES"
title = "EXPLAIN-obligation proof gate for waived SQL performance findings"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M2Y1SS0WSW1HNM4S14V8BH51"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5339"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/gates/_sql_explain_obligation.py", "tests/fixtures/sql/explain/**", "tests/unit/test_sql_explain_obligation.py", "docs/modules/gates.md", "src/frob/gates/_waive.py"]

[[links]]
kind = "blocked-by"
target = "01M336K76Q5R8CXT8A8RD54F31"
+++

A query flagged by 5148-2's performance rules carries a frob:tests-style obligation requiring an attached EXPLAIN ANALYZE artifact before a frob:waive on that finding is accepted -- reuse the closest existing 'proof required before waiver' precedent in frob.gates (grep for frob:invariant's binding mechanism) rather than inventing a new obligation shape. Fixture: a waiver attempt with and without the attached EXPLAIN artifact.
