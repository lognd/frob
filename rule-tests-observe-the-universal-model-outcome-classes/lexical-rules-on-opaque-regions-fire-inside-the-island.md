+++
id = "01M48Q4FV1V0ZRM8C4J1YMJ2G9"
title = "Lexical rules on opaque regions: fire inside the island, structural rules Unresolved over it"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:41:02Z"
updated = "2026-10-06T13:41:02Z"
scope = ["crates/gob-mdtest/**", "crates/*/tests/mdtest/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q4CHCFKJ9SSTVT471060B"

[[acceptance]]
text = "each lexical rule has a fire-inside-opaque case"
bound = false

[[acceptance]]
text = "a structural rule over the same island is Unresolved"
bound = false
+++

testing.md 3 (lexical rule row): universal-model.md 2.2 item 4 lets text, literals and prose queries read opaque payloads; add an mdtest section type with a lexical fire inside an opaque island (shell in YAML, #if 0, template literal) beside an Unresolved structural rule over the same island. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
