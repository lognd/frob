+++
id = "01M4GRAVWQ8W227X5E335CQFYN"
title = "Docs consolidation audit: inventory every markdown file, propose an organized information architecture (merges, supersessions, index, status headers), owner approves before any move"
type = "docs"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T16:35:41Z"
updated = "2026-10-09T16:35:41Z"
scope = ["notes/review/docs-consolidation-*", "changelog.d/**"]

[[acceptance]]
text = "Given every *.md in the repository (docs/design, docs/guides, docs/reference, notes, crate READMEs), when the audit lands, then notes/review/docs-consolidation-2026-10-09.md holds an inventory (path, size, purpose, status, last change, inbound frob:doc/links), the duplication and supersession map, a proposed target tree with every old path mapped to a new one, the frob:doc anchor and DRIFT impact of each move, and a phased execution plan"
bound = false
+++

Owner 2026-10-09: 'go through all the markdowns and start consolidating; everything looks like a blob of data; I would rather it be far more organized'. Proposal only; moves happen in follow-up tickets after owner approval.
