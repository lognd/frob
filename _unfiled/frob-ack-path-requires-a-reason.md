+++
id = "01M7EX854F06ABNHZ0BRHMFJ00"
title = "frob ack <path> requires a reason"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:10:26Z"
updated = "2026-11-15T06:10:26Z"
labels = ["no-story"]

[[acceptance]]
text = "ack without a reason exits non-zero (test)"
bound = false

[[acceptance]]
text = "Reason is stored and shown by graph why"
bound = false
+++

Source: frob-audit-core.md L7, meta M12. Evidence: crates/frob-ack/src/ack.rs accepts no reason. Remedy: require --reason and store it in frob.lock; relates to ~R8NFWKA. Files: crates/frob-ack/src/ack.rs, CLI wiring.
