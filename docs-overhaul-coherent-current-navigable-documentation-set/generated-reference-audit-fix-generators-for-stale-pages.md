+++
id = "01M67VEKFP0KTW41E9JBHTWWE5"
title = "Generated reference audit: fix generators for stale pages"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:08:37Z"
updated = "2026-10-31T02:08:37Z"
idempotency_key = "docs-ovh-gen"
scope = ["crates/gob-dev/src/render/**"]

[[acceptance]]
text = "gob-dev gen all --check clean; stale or empty generated pages traced to generator fixes in render code, not hand edits; reference index complete"
bound = false
+++

 Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
