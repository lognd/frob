+++
id = "01M3ZZG9SV29N5EKYRK2NAP90Y"
title = "Doc consistency: SYNC rule family, include regions, paired sections, checked facts (D84)"
type = "docs"
category = "todo"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T04:14:08Z"
updated = "2026-10-03T04:14:08Z"
idempotency_key = "m2-doc-consistency-design"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given doc-consistency.md, when read, then each mechanism has its directive or syntax, rule ids, fixes, and an example, and the decision log row D84 exists"
bound = false
+++

Owner request 2026-10-03: design a doc consistency rule family that stops drift within docs, between docs and between docs and code, and generate wherever possible. Write docs/design/doc-consistency.md: single source first (include regions from markdown sections and code regions, generated summaries such as the decision log), symmetric same-as pairs recorded in frob.lock (the doc-to-doc ack edge), checked fact references (CLI verbs and flags, config keys and defaults, rule ids and their single definition, decision ids, paths, enumerates), canonical definitions with near-duplicate detection; the engine in a product-neutral gob crate; fixes with applicability; self-application to this repository (the planner's 15 contradictions as the first corpus). Evidence: notes/research/docs-survey.md and the pending notes/research/docgen-survey.md.
