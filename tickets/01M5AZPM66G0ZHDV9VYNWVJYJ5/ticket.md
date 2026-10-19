+++
id = "01M5AZPM66G0ZHDV9VYNWVJYJ5"
title = "Coverage meta-test: lexical-rule opaque-region fire case needs a RuleMeta needs field"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-19T21:04:55Z"
updated = "2026-10-19T21:04:55Z"
scope = ["crates/gob-mdtest/**", "crates/gob-rules/**"]
+++

testing.md 3 requires a fire inside an opaque region for lexical rules, but RuleMeta carries no needs; add it, then a CaseKind for it. Found while working ~WPZC326.
