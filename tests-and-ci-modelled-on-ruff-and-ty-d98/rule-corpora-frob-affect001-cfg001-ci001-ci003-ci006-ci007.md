+++
id = "01M4YBK7YTVNC16GHFFK4JKY97"
title = "Rule corpora (frob): AFFECT001 CFG001 CI001 CI003 CI006 CI007 CI010 CI014 COV003"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M480C43A6BCH54NX8C5DQ4WJ"
reporter = "lognd"
created = "2026-10-14T23:22:40Z"
updated = "2026-10-15T01:59:45Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/gob-config/Cargo.toml", "crates/gob-config/tests/**", "crates/frob-ack/Cargo.toml", "crates/frob-ack/tests/**", "crates/frob-check/tests/**", "docs/reference/rules/**"]

[[acceptance]]
text = "AFFECT001 CFG001 CI001 CI003 CI006 CI007 CI010 CI014 each have an mdtest fire/clean pair and their allowlist entries are deleted; rule_coverage passes (COV003 split to ~0JTK1XS)"
bound = true
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md, examples in crates/frob-obligations/tests/mdtest) for these rules, then delete their allowlist entries. Do not allowlist new gaps.
