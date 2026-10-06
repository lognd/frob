+++
id = "01M48PBZRJ30T8TKEE31X6M6MS"
title = "gob-mdtest: strict mode, any unmatched finding fails the case"
type = "story"
category = "todo"
priority = "high"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:39Z"
updated = "2026-10-06T13:41:02Z"
scope = ["crates/gob-mdtest/**", "crates/*/tests/mdtest/**"]

[[acceptance]]
text = "a self-test where a second rule fires unexpectedly fails"
bound = false

[[acceptance]]
text = "all existing corpora pass after migration"
bound = false

[[acceptance]]
text = "an Unresolved or Advisory finding of a selected rule that no marker matches fails the case, and a rolled-up spanless Unresolved is matched by a header assertion"
bound = false

[[acceptance]]
text = "the unmatched-finding report prints class, severity and reason"
bound = false
+++

The runner silently drops findings from rules other than the block rule and marker rules (crates/gob-mdtest/src/run.rs:174). Select the rules a case runs (section config, default the block rule plus marker rules) and fail on any selected finding no marker matches, reported as an unexpected finding like ty. Migrate the existing corpora, adding explicit markers where rules legitimately co-fire. Source: notes/research/rule-testing.md (D103).
