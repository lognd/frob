+++
id = "01M5AZPM66G0ZHDV9VYNWVJYJ5"
title = "Coverage meta-test: lexical-rule opaque-region fire case needs a RuleMeta needs field"
type = "task"
category = "in-progress"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-19T21:04:55Z"
updated = "2026-10-20T02:30:52Z"
scope = ["crates/gob-mdtest/**", "crates/gob-rules/**", "crates/gob-macros/src/rule_attr.rs", "crates/gob-macros/src/lib.rs", "crates/gob-diagnostics/tests/contract.rs", "crates/grimble-check/src/product.rs", "crates/gob-config/src/rules/cfg001.rs", "crates/gob-check/src/status.rs", "crates/gob-check/src/required.rs", "crates/gob-check/tests/ui_product/retired_reused.rs", "crates/gob-check/tests/ui_product/dup_id.rs", "crates/gob-check/tests/ui_product/dup_slug.rs", "crates/gob-dev/src/render/rules.rs", "crates/crunk-rules/tests/rules.rs", "crates/gob-macros/tests/**", "docs/design/rules.md"]

[[acceptance]]
text = "A lexical rule (needs = Lexical) is required by the coverage meta-test to carry an opaque_fire case (expect=fire cell=island)"
bound = false
+++

testing.md 3 requires a fire inside an opaque region for lexical rules, but RuleMeta carries no needs; add it, then a CaseKind for it. Found while working ~WPZC326.
