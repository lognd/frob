+++
id = "01M3ZX83T22GTC94BW4PM742G1"
title = "GitHub adapter renders projection sections to markdown, labels and hidden marker"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T03:34:42Z"
idempotency_key = "m2-mirror-gh-render"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/github/render.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[acceptance]]
text = "Given a projection, when rendered, then the body has the documented sections and the managed notice and the digest equals the projection render digest"
bound = false

[[acceptance]]
text = "Given the same projection twice, when rendered, then the output is byte-identical"
bound = false
+++

Implements mirror.md sections 2 and 2.1.

Section kinds map to headings; scope, evidence and leases are a generated read-only block; ULID in a hidden body marker plus a label.
