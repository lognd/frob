+++
id = "01M48R03ZFTPSDD33HMJBD7STD"
title = "Migrate gob-check neutral rules, gob-directives and tool-bound rules; PROC001 into one file"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:07Z"
updated = "2026-10-08T03:51:50Z"
scope = ["crates/gob-check/**", "crates/gob-directives/**", "crates/gob-exec/**"]

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "PROC001 results identical"
bound = false

[[acceptance]]
text = "no rule id string literal remains in tool parsing except external tool id maps"
bound = false
+++

M6c: the Stage body kind for tool-emitted rules; PROC001's scanner moves into its rule file and uses the shared walk. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
