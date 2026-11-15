+++
id = "01M7EXQXJ83MCDA8QFTK9BJ1B7"
title = "record agent vs human on every exception and refuse identical-reason bulk acks"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:19:02Z"
updated = "2026-11-15T06:19:02Z"
labels = ["no-story"]
+++

Source: frob-audit-meta.md M12. Evidence: exceptions carry no actor kind. Remedy: store actor kind; refuse N acks with one reason. Related ~R8NFWKA. Files: crates/frob-obligations/src/exc.rs, frob-ack.
