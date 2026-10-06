+++
id = "01M48Q4CHCFKJ9SSTVT471060B"
title = "gob-mdtest: outcome classes unresolved and notapplicable, subject accounting, certified clean"
type = "story"
category = "todo"
priority = "high"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:40:59Z"
updated = "2026-10-06T13:40:59Z"
scope = ["crates/gob-mdtest/**", "crates/*/tests/mdtest/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q4BZHFXT3GMYDKYR7MCXF"

[[acceptance]]
text = "a rule that examines nothing fails an expect=clean block"
bound = false

[[acceptance]]
text = "an Unresolved-only result fails expect=fire and an Error fails expect=unresolved"
bound = false

[[acceptance]]
text = "a wrong reason code fails"
bound = false

[[acceptance]]
text = "a NotApplicable result fails expect=clean and passes expect=notapplicable"
bound = false

[[acceptance]]
text = "FORMAT.md documents the vocabulary"
bound = false
+++

testing.md 1-2: expect=fire|clean|unresolved|notapplicable, markers advisory: and unresolved[REASON]: with required, subjects= / subjects>= (clean defaults to >=1), fidelity=, parse=, spanless header assertions, known-gap and fixed modifiers shared with GRL section 9. Migrate inv002.md (its unresolved case is an unmarked fire) and add Unresolved blocks to cov001, doc001, todo001, ref001. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
