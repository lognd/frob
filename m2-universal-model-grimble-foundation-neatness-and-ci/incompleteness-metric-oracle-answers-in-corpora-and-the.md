+++
id = "01M4CXSZ5PYK101KSEH6SJ9WYR"
title = "Incompleteness metric: oracle answers in corpora and the false-Unknown rate per language in CI"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:35Z"
updated = "2026-10-22T09:52:03Z"
scope = ["changelog.d/**", "crates/gob-testsupport/**", "crates/gob-check/**", "docs/design/testing.md"]

[[acceptance]]
text = "Given the corpus, when CI runs, then the false-Unknown rate per language and capability is reported and a rise fails like a regression; a false Must fails always"
bound = false
+++

docs/design/cohesion.md 2.3; testing.md corpora gain an oracle column.
