+++
id = "01M5HT58NK23KQMMVXD1FZ0R2D"
title = "Min unit case count thresholds per scope as COV rule"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T12:42:45Z"
updated = "2026-11-16T12:05:12Z"
labels = ["no-story"]
scope = ["crates/frob-obligations/**", "docs/reference/rules/COV005.md", "docs/reference/rules/README.md", "docs/reference/config/frob.md", "docs/schemas/config.json", "crates/frob/src/explain_cmd.rs", "docs/README.md"]

[[acceptance]]
text = "Given a scope whose unit case count is below its configured minimum, when frob check runs, then a COV rule finding names the scope and the shortfall; at or above the minimum it passes"
bound = true
+++

found while working ~0MQ76H2: the min unit cases half of the v1 [testing] thresholds is not implemented; only line/branch percent (COV004) is.

no-story: internal engineering task in frob-obligations; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
