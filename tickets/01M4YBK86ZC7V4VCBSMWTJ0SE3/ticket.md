+++
id = "01M4YBK86ZC7V4VCBSMWTJ0SE3"
title = "Rule corpora (frob): TICK001-005 TICK007-009 TOOL001 TOOL002"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M480C43A6BCH54NX8C5DQ4WJ"
reporter = "lognd"
created = "2026-10-14T23:22:40Z"
updated = "2026-10-15T14:13:24Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/frob-check/tests/**", "docs/reference/rules/TICK00*.md", "docs/reference/rules/TOOL00*.md", "changelog.d/01M4YBK86ZC7V4VCBSMWTJ0SE3.*"]

[[acceptance]]
text = "Each listed rule has an mdtest fire/clean pair or fixture; its [[gap]] entry is deleted from crates/gob-mdtest/coverage-allowlist.toml; the product's rule_coverage test passes"
bound = true
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md, example crates/frob-pm/tests/corpus.rs) for these rules, then delete their allowlist entries.
