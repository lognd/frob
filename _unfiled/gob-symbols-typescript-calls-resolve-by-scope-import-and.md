+++
id = "01M5HT1NDW38SMA2P17A0B2BDV"
title = "gob-symbols: typescript::calls_resolve_by_scope_import_and_receiver fails on experimental"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T12:40:47Z"
updated = "2026-10-22T15:06:56Z"
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "Given the typescript calls_resolve_by_scope_import_and_receiver test, when run, then it passes with the root cause fixed"
bound = true
+++

Found while working B077GY9: fails identically with and without that change (tests/it/typescript.rs:419 expects Some(May), got None).
