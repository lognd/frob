+++
id = "01M4PQ6C6RQWFSHHS3EPKVAH8E"
title = "GRL002 and GRL007: parse snippets in their language, as KIND selection, as roles lifting"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-12T00:11:26Z"
updated = "2026-10-28T12:55:58Z"
labels = ["no-story"]
scope = ["crates/gob-plan/src/check/snippets.rs", "crates/gob-plan/src/grl/snippet.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7E5VPTH8J16D5APQDEAP"

[[links]]
kind = "blocked-by"
target = "01M4PPRHCTN3TZ0TJF8NRQ4KHD"

[[acceptance]]
text = "Given a snippet that does not parse in its language, when compiled, then GRL002 shows the parse tree it got and suggests as KIND (golden byte-equal)"
bound = false

[[acceptance]]
text = "Given an as roles snippet holding a node with no universal operator, when compiled, then GRL007 names the node (golden byte-equal)"
bound = false
+++

Remainder of ~APQDEAP split off: parse snippets through the grammar engine of gob-pattern (G17b), GRL002 shows the parse tree and suggests as KIND, as KIND selects a context-only construct, as roles lifts to U and GRL007 names a node with no universal operator.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
