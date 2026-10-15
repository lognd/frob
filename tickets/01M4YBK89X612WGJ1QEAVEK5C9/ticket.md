+++
id = "01M4YBK89X612WGJ1QEAVEK5C9"
title = "Rule corpora (grimble): MDL000-MDL010"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M480C4GC6M96Y0BQ9QSK0WB1"
reporter = "lognd"
created = "2026-10-14T23:22:40Z"
updated = "2026-10-15T15:09:07Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/grimble-check/tests/**", "docs/reference/rules/**"]

[[acceptance]]
text = "Each listed rule has an mdtest fire/clean pair or fixture; its [[gap]] entry is deleted from crates/gob-mdtest/coverage-allowlist.toml; the product's rule_coverage test passes"
bound = true
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md) for these rules, then delete their allowlist entries.
