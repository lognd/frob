+++
id = "01M48PC09SX0KFAM4B3V88AAXW"
title = "gob-mdtest: section tests, multi-file cases and toml config blocks with inheritance"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:40Z"
updated = "2026-10-22T04:35:06Z"
scope = ["crates/gob-mdtest/**", "crates/frob-obligations/tests/**", "docs/reference/rules/DOC002.md", "changelog.d/01M48PC09SX0KFAM4B3V88AAXW.added.md"]

[[links]]
kind = "blocked-by"
target = "01M48PBZRJ30T8TKEE31X6M6MS"

[[acceptance]]
text = "a cross-file corpus for a link rule passes"
bound = true

[[acceptance]]
text = "an inherited-config test passes"
bound = true

[[acceptance]]
text = "a section that is both test and group is a parse error"
bound = false

[[acceptance]]
text = "a case may mix languages (one block per file with its own fidelity), the assertion applies to the union, and a [mdtest] languages list selects matrix cells"
bound = false

[[acceptance]]
text = "existing mdtest corpora still pass after the heading-tree rewrite"
bound = false
+++

Replace the h1/h2 name string with a heading tree: a section is a test or a group, never both; blocks without file= merge in order, blocks with file= become extra files of one case; a toml fence configures the section and its descendants, child overriding parent (ty mdtest). Removes the frob-obligations side-file workaround (crates/frob-obligations/tests/corpus.rs). Source: notes/research/rule-testing.md (D103).
