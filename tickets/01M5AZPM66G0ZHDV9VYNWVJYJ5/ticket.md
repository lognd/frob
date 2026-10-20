+++
id = "01M5AZPM66G0ZHDV9VYNWVJYJ5"
title = "Coverage meta-test: lexical-rule opaque-region fire case needs a RuleMeta needs field"
type = "task"
category = "in-progress"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-19T21:04:55Z"
updated = "2026-10-20T02:20:02Z"
scope = ["crates/gob-mdtest/**", "crates/gob-rules/**", "crates/gob-macros/src/rule_attr.rs", "crates/gob-macros/src/lib.rs", "crates/gob-diagnostics/tests/contract.rs"]
+++

testing.md 3 requires a fire inside an opaque region for lexical rules, but RuleMeta carries no needs; add it, then a CaseKind for it. Found while working ~WPZC326.
