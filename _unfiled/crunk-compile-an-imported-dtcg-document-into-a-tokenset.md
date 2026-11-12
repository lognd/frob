+++
id = "01M5GY2Z3XXW99X7S02KZVBBSN"
title = "crunk: compile an imported DTCG document into a TokenSet"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T04:32:09Z"
updated = "2026-11-12T07:22:01Z"
labels = ["no-story"]
scope = ["crates/crunk-tokens/**", "changelog.d/01M5GY2Z3XXW99X7S02KZVBBSN.*"]

[[acceptance]]
text = "Given a valid DTCG document, when it is compiled, then a TokenSet holding every token with its resolved value is returned"
bound = true
+++

found while working ~62C50FH

no-story: internal engineering task in crunk-tokens; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
