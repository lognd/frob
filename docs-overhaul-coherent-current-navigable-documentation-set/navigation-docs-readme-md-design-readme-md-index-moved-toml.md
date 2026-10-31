+++
id = "01M67VEK6J4Z3ZGFTCNG4WRKHY"
title = "Navigation: docs/README.md, design/README.md index, MOVED.toml, assets"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:08:37Z"
updated = "2026-10-31T02:08:37Z"
idempotency_key = "docs-ovh-nav"
scope = ["docs/README.md", "docs/design/README.md", "docs/MOVED.toml", "docs/assets/**"]

[[acceptance]]
text = "docs/README.md lists every top-level area; design/README.md indexes all design pages with status; no orphan pages (every md reachable from an index); MOVED.toml entries resolve"
bound = false
+++

Land after content tickets to index final names. Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
