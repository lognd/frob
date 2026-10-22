+++
id = "01M5HT1NDW38SMA2P17A0B2BDV"
title = "gob-symbols: typescript::calls_resolve_by_scope_import_and_receiver fails on experimental"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T12:40:47Z"
updated = "2026-10-22T12:40:47Z"
scope = ["crates/gob-symbols/**"]
+++

Found while working B077GY9: fails identically with and without that change (tests/it/typescript.rs:419 expects Some(May), got None).
