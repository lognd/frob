+++
id = "01M7EX90RQP68MN4HDE0PA41FP"
title = "profile budget and timeout raises need a perf ticket and an expiry"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:10:54Z"
updated = "2026-11-15T06:14:01Z"
labels = ["no-story"]

[[acceptance]]
text = "A raise without ticket and expiry is a finding (test)"
bound = false
+++

Source: frob-audit-meta.md M5. Evidence: budget/timeout raises in frob.toml carry no justification. Remedy: a rule requiring a ticket ref and until= date on a raise. Files: crates/gob-config, frob.toml, rule pack.
