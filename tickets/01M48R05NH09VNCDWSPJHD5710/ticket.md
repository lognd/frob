+++
id = "01M48R05NH09VNCDWSPJHD5710"
title = "The colocated .md is docs and corpus: rule_suite!, derived language matrix cases, outcome classes"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:09Z"
updated = "2026-10-06T13:56:09Z"
scope = ["crates/gob-mdtest/**", "crates/gob-check/**", "crates/*/src/rules/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q4CHCFKJ9SSTVT471060B"

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "a deliberately wrong derived-matrix expectation fails naming rule and language"
bound = false

[[acceptance]]
text = "the coverage allowlist file is deleted once gaps are pending(..) on the rules"
bound = false
+++

M9: run each rule's .md through the product harness with the D106 outcome classes; derived matrix cases; the coverage allowlist becomes per-rule corpus = pending(~ticket) checked by the macro. Supersedes ~HDFYHNJ. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
