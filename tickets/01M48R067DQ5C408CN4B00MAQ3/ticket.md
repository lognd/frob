+++
id = "01M48R067DQ5C408CN4B00MAQ3"
title = "Generate rule pages and the per-rule language matrix from the rule's own .md"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:10Z"
updated = "2026-10-06T13:56:10Z"
scope = ["crates/gob-dev/**", "docs/reference/**"]

[[links]]
kind = "blocked-by"
target = "01M48R01QSDTBKNPREQPBJ6GPZ"

[[acceptance]]
text = "docs/reference/rules has a page for every rule of every product"
bound = false

[[acceptance]]
text = "a stale page fails cargo test -p gob-dev naming the path"
bound = false
+++

M10: rule pages, the languages page and the per-rule matrix are generated kinds with freshness tests, reading each rule's .md. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
