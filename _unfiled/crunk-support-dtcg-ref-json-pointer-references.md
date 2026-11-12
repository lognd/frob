+++
id = "01M5GY2ZEA492MTNPXVHEV60AY"
title = "crunk: support DTCG $ref JSON-pointer references"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T04:32:10Z"
updated = "2026-11-12T07:42:31Z"
labels = ["no-story"]
scope = ["crates/crunk-tokens/**", "changelog.d/01M5GY2ZEA492MTNPXVHEV60AY.*"]

[[acceptance]]
text = "Given a DTCG token whose value is a $ref JSON-pointer into the same document, when the document is compiled, then the token resolves to the referenced token's value and an unresolvable pointer is refused with an error naming it"
bound = true
+++

found while working ~62C50FH

no-story: internal engineering task in crunk-tokens; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
