+++
id = "01M4MBJ30F849Z0DD5XRNFJTE8"
title = "FileCx carries the file path and language so file rules can pick a grammar"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-11T02:09:38Z"
updated = "2026-10-31T08:12:47Z"
labels = ["no-story"]
scope = ["crates/gob-rules/src/decl.rs", "crates/gob-check/src/**", "crates/gob-rules/src/index.rs", "crates/gob-rules/Cargo.toml", "crates/gob-rules/tests/rule_attr.rs", "Cargo.lock"]

[[acceptance]]
text = "FileCx exposes the file path and detected language to file rules, with a unit test showing a rule can select a grammar from it"
bound = false

[[acceptance]]
text = "All existing file rules still compile and pass unchanged"
bound = false
+++

found while working ~K4B9CKF: #[rule] FileRule::check gets only text, so a syntactic rule over several languages cannot choose a grammar; ERR001-ERR003 need it

no-story: internal engineering task in gob-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
