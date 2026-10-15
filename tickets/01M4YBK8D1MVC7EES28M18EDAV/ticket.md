+++
id = "01M4YBK8D1MVC7EES28M18EDAV"
title = "Rule corpora (grimble): MDL011-MDL021"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M480C4GC6M96Y0BQ9QSK0WB1"
reporter = "lognd"
created = "2026-10-14T23:22:40Z"
updated = "2026-10-15T16:06:27Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/grimble-check/tests/mdtest/**"]

[[acceptance]]
text = "Each listed rule has an mdtest fire/clean pair or fixture; its [[gap]] entry is deleted from crates/gob-mdtest/coverage-allowlist.toml; the product's rule_coverage test passes"
bound = true
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md) for these rules, then delete their allowlist entries.
