+++
id = "01M7EXRDAGY3M6ZGQQWR8M2ET6"
title = "crunk render: rasterise layout solve to PNG/SVG with --image"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETK794J40RVB9YAWNQ6NF3"
reporter = "lognd"
created = "2026-11-15T06:19:18Z"
updated = "2026-11-15T06:19:18Z"
idempotency_key = "crunkplan-cfcaa9a27339"
labels = ["no-story"]

[[acceptance]]
text = "crunk render --image writes a PNG and an SVG for a scene in the default build"
bound = false

[[acceptance]]
text = "output is deterministic: two runs give identical bytes (test)"
bound = false

[[acceptance]]
text = "a scene with no solve yields an Unresolved finding, not a blank image"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H1.
Evidence: render emits no pixels in the default build
Remedy: rasterise the T1 layout solve (boxes, text) to PNG and SVG behind crunk render --image
Crates/files: crates/crunk/src/render.rs, crates/crunk-gallery
Verify against HEAD first; the audit ran on a stale binary.
