+++
id = "01M7BJPF2BB15JWV88XXFEA9MD"
title = "CYCLE001 anchors a repo-wide May-edge component to the first file and cannot be waived"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-13T23:08:17Z"
updated = "2026-11-13T23:11:31Z"
idempotency_key = "cycle001-root-anchor"
labels = ["audit"]
scope = ["crates/grimble-arch/**"]

[[acceptance]]
text = "CYCLE001 skips the unnamed root node or anchors at a member symbol so frob:accept binds; the full-repo scan no longer reports a cycle through every crate"
bound = false
+++

Implementer found cone-compare.py imports only stdlib; moving it re-anchors the finding to the next alphabetical file. cycle::report takes the minimum first_file across members; the component is the root node plus ~70 crates joined by May edges only. Fix in crates/grimble-arch/src/cycle.rs: drop the root node or require a Must edge for non-crate files, or anchor at a real symbol.
