+++
id = "01M48PC1C64V7SN640NSASXGW5"
title = "gob-mdtest: contain panics and support expect-panic"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:41Z"
updated = "2026-10-22T02:55:48Z"
scope = ["crates/gob-mdtest/**"]

[[acceptance]]
text = "a panicking rule is reported as a failed case, not an aborted run"
bound = true

[[acceptance]]
text = "expect-panic passes on a matching panic and fails when there is none"
bound = true

[[acceptance]]
text = "each adapter has a garbage-input case asserting Unresolved or NotApplicable and no panic"
bound = true

[[acceptance]]
text = "expect-panic with an empty substring accepts any panic but still requires one"
bound = true

[[acceptance]]
text = "a non-string panic payload is reported with a placeholder"
bound = true

[[acceptance]]
text = "directive binds to the next case only and CRLF does not shift line attribution"
bound = true

[[acceptance]]
text = "panics on parallel threads do not leak between threads"
bound = false

[[acceptance]]
text = "check_garbage reports panics, errors and silence per cell and passes Unresolved or NotApplicable"
bound = false
+++

Wrap each case in catch_unwind, attribute a panic to its markdown line, and support `<!-- expect-panic: substring -->` with the inverse failure when no panic happens (ty mdtest). Source: notes/research/rule-testing.md (D103).
