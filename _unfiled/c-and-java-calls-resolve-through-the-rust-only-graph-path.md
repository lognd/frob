+++
id = "01M7BSMQWJ77EENS87BQBQWFB4"
title = "C and Java calls resolve through the Rust-only graph path (DEAD001 false positives likely)"
type = "bug"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-14T01:09:40Z"
updated = "2026-11-14T01:52:32Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "A called private C and Java function has no DEAD001."
bound = false
+++

Found while fixing SY378XX: graph.rs falls through to Rust-only resolution for C and Java. Confirm with a fixture, then add resolvers like graph/go.rs.
