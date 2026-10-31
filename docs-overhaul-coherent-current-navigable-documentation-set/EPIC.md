+++
id = "01M67VDQ8WGS0SYG4J4NFXNQJE"
title = "Docs overhaul: coherent, current, navigable documentation set"
type = "epic"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T02:08:08Z"
updated = "2026-10-31T02:08:08Z"
idempotency_key = "docs-overhaul-epic"

[[acceptance]]
text = "All child tickets landed; docs/README.md indexes every page; link check green; no stale Python-era, ramp-in or warn-new-rules text outside history"
bound = false
+++

Owner reports docs are a mess. Survey 2026-10-30: 355 md files (280 generated under docs/reference), design/ has 51 files (up to 1753 lines), crunk described as separate repo in several design pages, ramp-in and warn-new-rules text in design/rules.md and design/architecture.md, Python-era text in design/* and guides/quickstart.md, overlap between crunk/migration.md, crunk/hullbreach-migration.md, migration/crunk-import.md, design/migration.md, guides/upgrade-from-v1.md. Generated docs (docs/reference/**, docs/schemas/**) are never hand-edited; use gob-dev gen all. Respect docs/design/documentation.md, frob:doc and frob ack. Not on a milestone or cycle.
