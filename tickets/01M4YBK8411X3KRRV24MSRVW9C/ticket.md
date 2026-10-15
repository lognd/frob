+++
id = "01M4YBK8411X3KRRV24MSRVW9C"
title = "Rule corpora (frob): DRIFT001-004 EXC005 PERF001 PROC001 READ001 SCOPE001 SIB001 TEST001"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M480C43A6BCH54NX8C5DQ4WJ"
reporter = "lognd"
created = "2026-10-14T23:22:40Z"
updated = "2026-10-15T06:17:57Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml", "crates/frob-check/**", "docs/reference/rules/**"]

[[acceptance]]
text = "Each listed rule has an mdtest fire/clean pair or fixture; its [[gap]] entry is deleted from crates/gob-mdtest/coverage-allowlist.toml; the product's rule_coverage test passes"
bound = true
+++

Write mdtest suites (see crates/gob-mdtest/FORMAT.md, example crates/frob-check/tests/grl_corpus.rs) for these rules, then delete their allowlist entries.
