+++
id = "01M7EXR1787ZYMM49F73JDA88M"
title = "layering allow-list rows must not cite closed tickets"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:19:06Z"
updated = "2026-11-15T06:19:06Z"
labels = ["no-story"]
+++

Source: frob-audit2-repo.md M3/F8. Evidence: crates/gob-dev/tests/it/layering.rs:13-24 cites closed ~M8WETW7. Remedy: re-ticket and add a test that cited tickets are open. Files: layering.rs.
