+++
id = "01M7EXQZ1Y40N29PF0ZGD3T68Q"
title = "ticket doable: do not report STALE while a finished refresh holds the lock"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:19:04Z"
updated = "2026-11-15T06:19:04Z"
labels = ["no-story"]
+++

Source: frob-audit-meta.md L2. Evidence: crates/frob/tests/it/sync_policy.rs flake class. Remedy: treat a lock held by a finished refresh as fresh. Files: sync policy code.
