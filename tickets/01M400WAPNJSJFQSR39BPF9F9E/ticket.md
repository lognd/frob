+++
id = "01M400WAPNJSJFQSR39BPF9F9E"
title = "enumerates: claim shapes (tables, lists, headings, whole sections), key extraction and fix placement"
type = "docs"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T04:38:10Z"
updated = "2026-10-03T04:42:01Z"
idempotency_key = "m2-enumerates-shapes"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given doc-consistency.md 5.0, when read, then every claim shape, key rule, extent rule and fix placement rule is specified with an example"
bound = false
+++

Owner question 2026-10-03: does enumerates detect tables, formatting, headings, subheadings? Specify the claim shapes (table key column, list items, member-per-heading, a whole section across subsections), key extraction and normalization (code spans, links, emphasis, member names: identifier, serde or clap rename, display), the claim's extent, duplicates, fixes that write in the shape of the existing block and keep its sort order, and the extraction work needed in the markdown adapter (tree-sitter-md pipe_table, list, list_item; headings exist today).
