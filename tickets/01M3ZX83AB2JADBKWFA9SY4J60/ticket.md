+++
id = "01M3ZX83AB2JADBKWFA9SY4J60"
title = "Tracker adapter trait and capabilities record (listing, history by event id, additive edits, journaled writes)"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T05:49:56Z"
idempotency_key = "m2-mirror-adapter-trait"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/adapter.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX832JK52FXBPPCCGTDRTG"

[[acceptance]]
text = "Given a fake adapter and a recorded projection, when the mirror runs offline, then operations are produced without network"
bound = false

[[acceptance]]
text = "Given an adapter declaring no native sub-issues, when relations are routed, then parent edges fall back to body links and the capabilities say so"
bound = false
+++

Implements mirror.md sections 2.1 and 3.2 to 3.4.

Trait: create (carrying a nonce, outcome created, failed or unknown), update, close with reason, list the bot's issues by creator newest first, read an issue, read history after an event id (entries carry actor user id, field, value digest, event id), add and remove labels and assignees (never replace-all), link, schema and inventory read; a capabilities record (native sub-issues, native links, custom fields, state reasons, history retention, markdown dialect). Recorded API fixtures so tests run offline.
