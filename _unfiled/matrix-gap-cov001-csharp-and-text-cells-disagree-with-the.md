+++
id = "01M5AG2DZAMJP4MBZAZVDJC1HF"
title = "Matrix gap: COV001 csharp and text cells disagree with the derived expectation"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T16:31:45Z"
updated = "2026-11-09T09:47:47Z"
scope = ["docs/**", "docs/reference/**", "crates/frob-obligations/src/cov.rs", "crates/frob-obligations/src/rules/cov001.md", "crates/frob-obligations/tests/mdtest/cov001.md", "crates/gob-mdtest/coverage-allowlist.toml"]
+++

COV001 needs test items at F2. The derivation says csharp (F1) and text (F0) are Unresolved, but the real pipeline warns on C# and reports nothing on text. Reconcile the rule/pipeline with the capability matrix, then fill the cells. Found while working ~42DZ0RZ.
