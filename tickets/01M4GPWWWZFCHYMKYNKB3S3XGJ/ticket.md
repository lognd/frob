+++
id = "01M4GPWWWZFCHYMKYNKB3S3XGJ"
title = "Leases: generated files (gen outputs) are shareable by default alongside declared append-only shared files"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T16:10:48Z"
updated = "2026-10-10T21:42:53Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-lease/**", "crates/gob-config/**", "changelog.d/**", "docs/reference/config.md", "docs/schemas/config.json", "docs/design/tickets.md"]

[[acceptance]]
text = "Given a ticket leasing docs/** and another ticket editing a generated file and an append-only registry inside it, when the second runs frob work, then no E-LEASE-HELD is raised for those files"
bound = true
+++

logand.app-v2 F-559: a broad integration lease blocked three tickets for 30+ minutes over a generated file and an append-only file.
