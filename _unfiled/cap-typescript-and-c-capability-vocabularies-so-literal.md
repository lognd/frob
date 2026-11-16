+++
id = "01M648G0AJCWY7TY7XBYHNK765"
title = "CAP: TypeScript and C# capability vocabularies so literal lookups yield findings"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T16:39:37Z"
updated = "2026-11-16T19:00:47Z"
scope = ["crates/gob-caps/**,crates/grimble-bind/src/caps.rs", "crates/gob-caps/**", "crates/grimble-bind/src/caps.rs", "crates/gob-ir/src/registry.rs"]

[[acceptance]]
text = "Given a TypeScript source that calls a literal capability callee (for example fs.readFileSync), when grimble check scans it, then the matching capability atom is reported as a use, proven by a test in crates/grimble-bind/src/caps.rs."
bound = true
+++

found while working ~6CV37RW: name lookups are resolved for TS/JS/C# in gob-symbols but scan_resolved is gated to rust|python and no TS/C# vocabulary exists.
