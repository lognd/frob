+++
id = "01M48PC1C64V7SN640NSASXGW5"
title = "gob-mdtest: contain panics and support expect-panic"
type = "story"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:41Z"
updated = "2026-10-06T13:41:09Z"
scope = ["crates/gob-mdtest/**"]

[[acceptance]]
text = "a panicking rule is reported as a failed case, not an aborted run"
bound = false

[[acceptance]]
text = "expect-panic passes on a matching panic and fails when there is none"
bound = false

[[acceptance]]
text = "each adapter has a garbage-input case asserting Unresolved or NotApplicable and no panic"
bound = false
+++

Wrap each case in catch_unwind, attribute a panic to its markdown line, and support `<!-- expect-panic: substring -->` with the inverse failure when no panic happens (ty mdtest). Source: notes/research/rule-testing.md (D103).
