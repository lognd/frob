+++
id = "01M680RDM5VDH85ZAD54YB9YQT"
title = "Docs: teach generated index the new doc dirs (consolidation phase 4)"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T03:41:21Z"
updated = "2026-10-31T03:41:21Z"
scope = ["crates/gob-dev/src/render/docs_index.rs", "docs/README.md", "docs/design/**"]

[[links]]
kind = "blocked-by"
target = "01M4GRAVWQ8W227X5E335CQFYN"

[[acceptance]]
text = "Given the moved clusters, when gob-dev gen all --check runs, then it is clean, docs/README.md lists the new dirs, and the decision log is split to design/decisions.md"
bound = false
+++

Do only after phase 3 lands.
