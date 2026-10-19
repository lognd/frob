+++
id = "01M48Q4DMNMQEYQNWPK42DZ0RZ"
title = "Universal-rule language matrix with expectations derived from needs and capability cells"
type = "story"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:41:00Z"
updated = "2026-10-19T16:43:25Z"
scope = ["crates/gob-mdtest/**", "crates/gob-check/**", "crates/*/tests/mdtest/**", "crates/frob-check/tests/rule_matrix.rs", "docs/design/testing.md", "docs/reference/rules/*.md"]

[[links]]
kind = "blocked-by"
target = "01M48Q4CHCFKJ9SSTVT471060B"

[[acceptance]]
text = "each Universal rule has every matrix cell or an allowlisted gap with a ticket"
bound = true

[[acceptance]]
text = "a hand-written expectation contradicting the derived one fails"
bound = true

[[acceptance]]
text = "parity cases pass for COV001 and TODO001"
bound = true
+++

testing.md 4: every Universal rule has a case per fidelity class (Rust F3, Python F2, TypeScript F2, C# F1, markdown F4, an adapter-less text file F0, a binary file, an embedded opaque island); the expected class per cell is derived from the rule's needs and the adapter capability cells, and a written expectation that disagrees fails; parity cases render one shape in three languages with one expectation. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
