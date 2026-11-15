+++
id = "01M7EXSB9M0RV1M2DQ9VMW9A1J"
title = "crunk review: scene, component and content files enter the review digest"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETK9M5AFFP3X5K1G8D4F4K"
reporter = "lognd"
created = "2026-11-15T06:19:49Z"
updated = "2026-11-15T06:19:49Z"
idempotency_key = "crunkplan-18114caf82e5"
labels = ["no-story"]

[[acceptance]]
text = "editing a scene file after an ack makes HUMAN001 fire (test)"
bound = false

[[acceptance]]
text = "digest of unchanged tree is stable"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H6.
Evidence: ack digest omits scene, component and content files so edits stay acked
Remedy: include them in the digest so any change makes HUMAN001 stale
Crates/files: crates/crunk-check/src/review.rs, crates/crunk-rules/src/review.rs
Verify against HEAD first; the audit ran on a stale binary.
