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
updated = "2026-10-03T05:49:57Z"
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

Implements mirror.md sections 2, 2.1 and 3.6 (one managed label).

Section kinds map to headings; scope, evidence and leases are a generated read-only block; the body carries the hidden marker string supplied by the marker ticket (m2-mirror-markers), and the one managed label frob:managed is applied, never a label per ULID. No task-list checkboxes. Text neutralisation and render limits are separate tickets (m2-mirror2-neutralise, m2-mirror2-render-limits) layered on this renderer.
