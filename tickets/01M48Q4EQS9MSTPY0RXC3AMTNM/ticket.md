+++
id = "01M48Q4EQS9MSTPY0RXC3AMTNM"
title = "Polarity-conformance corpus run against every shipped rule"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:41:01Z"
updated = "2026-10-06T13:41:01Z"
scope = ["crates/gob-ir/**", "crates/gob-mdtest/**", "crates/frob-obligations/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q4CHCFKJ9SSTVT471060B"

[[acceptance]]
text = "every shipped rule runs the polarity corpus"
bound = false

[[acceptance]]
text = "a P- rule that fires on May-only reach fails the test"
bound = false
+++

testing.md 7: a standard small repository per polarity (May-only edge, Must edge, opaque region, Unknown visibility) run against every shipped rule; a P- rule firing on a May-only reach fails (Theorem 3: never an Error whose premise is false). Port COV001's hand-rolled May logic onto the shared evaluator where practical. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
