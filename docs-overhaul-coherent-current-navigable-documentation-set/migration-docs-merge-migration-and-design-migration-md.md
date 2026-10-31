+++
id = "01M67VEK26XQF0CRQS7G7N1A3F"
title = "Migration docs merge: migration/** and design/migration.md"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:08:36Z"
updated = "2026-10-31T02:08:36Z"
idempotency_key = "docs-ovh-migration"
scope = ["docs/migration/**", "docs/design/migration.md"]

[[acceptance]]
text = "One canonical v1 and crunk import story; design/migration.md reduced to design rationale linking to migration/*; selection tomls documented; no duplicate text with guides/upgrade-from-v1.md (cross-link)"
bound = false
+++

 Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
