+++
id = "01M5XCZ18GTA7MKKF4Z0MD95W3"
title = "crunk status ID ready: handoff gate with design/review/*.toml anchored comments and changed marking"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:43:02Z"
updated = "2026-10-28T12:55:39Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk/src/status.rs, crates/crunk-spec/src/handoff.rs, crates/crunk-rules/src/handoff.rs, crates/crunk/tests/status_ready.rs"]

[[acceptance]]
text = "Given a screen with open blocking comments, a stale export, a missing code mapping or red lints at its tier, when crunk status ID ready runs, then it refuses naming each reason and records nothing; given all green, then the content hash is recorded in crunk.lock; given a later change to the screen, then it is marked changed. Edge cases: unknown id exits 2; a comment anchored to a deleted node is reported as orphaned and does not block; running ready twice is idempotent; human acks are never written by this verb"
bound = false
+++

Design crunk.md section 5 process row and section 8 handoff row; section 4.1 for lock semantics. Reuse the existing review/ack lock code.

no-story: internal engineering task in crunk; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
