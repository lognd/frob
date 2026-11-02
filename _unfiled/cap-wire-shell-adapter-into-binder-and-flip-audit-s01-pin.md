+++
id = "01M6CN4WNECMHQ1T65JT6CSE34"
title = "CAP: wire shell adapter into binder and flip audit s01 pin"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-01T22:54:39Z"
updated = "2026-11-02T00:12:15Z"
scope = ["crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "crates/grimble-check/tests/**", "crates/gob-directives/**", "crates/gob-plan/**"]
+++

found while working ~1PKHMPA: register a shell adapter, wire grimble-bind caps.rs (resolved_only, scan_resolved, UNMEASURED_EXTS), flip symbolic_audit s01 pin to resolved/Unresolved results, add Language::Shell to hash_comments in gob-directives scan.rs, add Lang::Shell to gob-caps.
