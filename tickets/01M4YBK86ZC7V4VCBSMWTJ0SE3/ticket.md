+++
id = "01M4YBK86ZC7V4VCBSMWTJ0SE3"
title = "Rule corpora (frob): TICK001-005 TICK007-009 TOOL001 TOOL002"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M480C43A6BCH54NX8C5DQ4WJ"
reporter = "lognd"
created = "2026-10-14T23:22:40Z"
updated = "2026-10-15T07:01:44Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/frob-check/tests/**"]

[[acceptance]]
text = "Each listed rule has an mdtest fire/clean pair or fixture; its [[gap]] entry is deleted from crates/gob-mdtest/coverage-allowlist.toml; the product's rule_coverage test passes"
bound = false
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md, example crates/frob-pm/tests/corpus.rs) for these rules, then delete their allowlist entries.
