+++
id = "01M48PC2EHP611CJ8H2MJG5PAQ"
title = "gob-mdtest: unknown directives and attribute keys are parse errors"
type = "story"
category = "todo"
priority = "low"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:42Z"
updated = "2026-10-06T13:41:08Z"
scope = ["crates/gob-mdtest/**", "crates/*/tests/mdtest/**"]

[[links]]
kind = "blocked-by"
target = "01M48PBZRJ30T8TKEE31X6M6MS"

[[acceptance]]
text = "parse tests for each case"
bound = false

[[acceptance]]
text = "all corpora pass or are fixed"
bound = false

[[acceptance]]
text = "an expect value outside fire, clean, unresolved, notapplicable is a parse error listing the allowed set"
bound = false
+++

Any HTML comment directive other than a known one (plus a small formatter allowlist) and any unknown info-string key are parse errors, and a fence with rule= but no expect= is an error instead of silent documentation (ty parser). Source: notes/research/rule-testing.md (D103).
