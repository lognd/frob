+++
id = "01M7EXSBXEPF76VTGQ8W0YFWC5"
title = "crunk ack: refuse when no render artifact exists"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETK9M5AFFP3X5K1G8D4F4K"
reporter = "lognd"
created = "2026-11-15T06:19:49Z"
updated = "2026-11-15T06:19:49Z"
idempotency_key = "crunkplan-7d4ec455acd9"
labels = ["no-story"]

[[acceptance]]
text = "ack on an unrendered subject exits with a typed error"
bound = false

[[acceptance]]
text = "ack after render succeeds"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H6.
Evidence: a screen can be acked without ever having been rendered
Remedy: refuse ack when no render artifact for the subject exists
Crates/files: crates/crunk/src/review.rs
Verify against HEAD first; the audit ran on a stale binary.
