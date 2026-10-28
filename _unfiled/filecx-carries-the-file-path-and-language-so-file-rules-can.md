+++
id = "01M4MBJ30F849Z0DD5XRNFJTE8"
title = "FileCx carries the file path and language so file rules can pick a grammar"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-11T02:09:38Z"
updated = "2026-10-28T12:56:00Z"
labels = ["no-story"]
scope = ["crates/gob-rules/src/decl.rs", "crates/gob-check/src/**"]
+++

found while working ~K4B9CKF: #[rule] FileRule::check gets only text, so a syntactic rule over several languages cannot choose a grammar; ERR001-ERR003 need it

no-story: internal engineering task in gob-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
