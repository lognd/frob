+++
id = "01M4YBK8G0M4TXBA0PWMNF5NYJ"
title = "Rule corpora (grimble): SYS001-SYS013 CAP001 CAP002"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M480C4GC6M96Y0BQ9QSK0WB1"
reporter = "lognd"
created = "2026-10-14T23:22:41Z"
updated = "2026-10-15T17:06:38Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/grimble-check/tests/mdtest/**"]

[[acceptance]]
text = "Each listed rule has an mdtest fire/clean pair or fixture; its [[gap]] entry is deleted from crates/gob-mdtest/coverage-allowlist.toml; the product's rule_coverage test passes"
bound = true
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md) for these rules, then delete their allowlist entries.
