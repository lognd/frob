+++
id = "01M6PB6EGHFWAVTMCR1TYNSKT5"
title = "docs: note unresolved warn mapping in packs-and-plugins.md"
type = "docs"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-11-05T17:13:09Z"
updated = "2026-11-06T19:12:48Z"
labels = ["no-story", "good-first"]
scope = ["docs/design/shared/packs-and-plugins.md"]

[[acceptance]]
text = "Given packs-and-plugins.md, when a reader looks up per-atom severity, then it states warn is emitted as Unresolved"
bound = true
+++

Document that a warn severity maps to Unresolved because the model has only Error and Unresolved.

## Start here

- Files to read first: docs/design/shared/packs-and-plugins.md
- Test command: frob check --files docs/design/shared/packs-and-plugins.md
- Who to ask: lognd
