+++
id = "01M5HMPQJH9F5WRY1HR5G8XEG9"
title = "tsc type facts: clean only if listed by --listFilesOnly, and detect tsconfig strict"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T11:07:26Z"
updated = "2026-11-12T22:51:36Z"
labels = ["no-story"]
scope = ["crates/gob-check/src/type_parse.rs", "crates/frob-check/src/typefacts.rs"]

[[acceptance]]
text = "A TypeScript file is marked type-clean only when tsc --listFilesOnly lists it (files outside tsconfig are not clean), covered by a test"
bound = false
+++

found while working ~69D9E89

no-story: internal engineering task in gob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
