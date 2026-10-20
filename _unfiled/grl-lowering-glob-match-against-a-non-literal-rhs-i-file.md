+++
id = "01M4XBAPBBMQ5TMT0EH30ZJZBC"
title = "GRL lowering: glob match against a non-literal rhs (i.file.path matches row.from)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T13:58:45Z"
updated = "2026-10-14T15:21:55Z"
scope = ["crates/gob-plan/**"]
+++

Found while working ~26X4K6K. INV002 matches a path against a side-row column or field, not a literal; convert.rs glob_literals refuses with 'a glob that is not a literal'. Needs an operand-pattern glob op in plan IR, codec, validate, executor.
