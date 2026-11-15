+++
id = "01M7EX854F06ABNHZ0BRHMFJ00"
title = "frob ack <path> requires a reason"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:26Z"
updated = "2026-11-15T06:10:26Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L7, meta M12. Evidence: crates/frob-ack/src/ack.rs accepts no reason. Remedy: require --reason and store it in frob.lock; relates to ~R8NFWKA. Files: crates/frob-ack/src/ack.rs, CLI wiring.
