+++
id = "01M7EX90RQP68MN4HDE0PA41FP"
title = "profile budget and timeout raises need a perf ticket and an expiry"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:54Z"
updated = "2026-11-15T06:10:54Z"
labels = ["no-story"]
+++

Source: frob-audit-meta.md M5. Evidence: budget/timeout raises in frob.toml carry no justification. Remedy: a rule requiring a ticket ref and until= date on a raise. Files: crates/gob-config, frob.toml, rule pack.
