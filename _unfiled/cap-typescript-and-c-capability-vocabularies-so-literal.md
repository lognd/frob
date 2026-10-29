+++
id = "01M648G0AJCWY7TY7XBYHNK765"
title = "CAP: TypeScript and C# capability vocabularies so literal lookups yield findings"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T16:39:37Z"
updated = "2026-10-29T16:39:37Z"
scope = ["crates/gob-caps/**,crates/grimble-bind/src/caps.rs"]
+++

found while working ~6CV37RW: name lookups are resolved for TS/JS/C# in gob-symbols but scan_resolved is gated to rust|python and no TS/C# vocabulary exists.
