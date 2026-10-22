+++
id = "01M5HT58K22KJXAE1MWHY3T79D"
title = "Fold coverage config and lcov report into repo-rule cache key"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T12:42:45Z"
updated = "2026-10-22T14:15:25Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "Given a change to the coverage thresholds config or the lcov report, when the product digest is computed, then the digest differs"
bound = false

[[acceptance]]
text = "Given an unchanged config and report, when the digest is computed twice, then it is identical"
bound = false
+++

found while working ~0MQ76H2: repo_digest in crates/frob-check/src/product.rs ignores the [coverage] table and the lcov report, so a cached COV004 result can go stale.
