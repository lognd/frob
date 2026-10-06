+++
id = "01M48R04HAG82FJV1T77Z6YH8P"
title = "Migrate grimble MDL and SYS rules to the two-file shape"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:08Z"
updated = "2026-10-06T13:56:08Z"
scope = ["crates/grimble-model/**", "crates/grimble-bind/**", "crates/grimble-check/**"]

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "grimble check output identical"
bound = false

[[acceptance]]
text = "every grimble rule has a generated docs page"
bound = false
+++

M7: each rule gets its two files with body = stage(ModelCheck or Binding); delete RULES, DIRECTIVE_RULES, declare_not_applicable and family filters. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
