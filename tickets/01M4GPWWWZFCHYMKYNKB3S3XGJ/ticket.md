+++
id = "01M4GPWWWZFCHYMKYNKB3S3XGJ"
title = "Leases: generated files (gen outputs) and declared append-only files are shareable by default, and lease scope can widen on demand as the diff grows"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T16:10:48Z"
updated = "2026-10-10T21:36:11Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-lease/**", "crates/gob-config/**", "changelog.d/**"]

[[acceptance]]
text = "Given a ticket leasing docs/** and another ticket editing a generated file and an append-only registry inside it, when the second runs frob work, then no E-LEASE-HELD is raised for those files"
bound = false

[[acceptance]]
text = "Given a ticket whose diff touches a file outside its scope that no other lease holds, when frob lease widen (or check --ticket with --widen) runs, then the scope grows to that file with a ledger event"
bound = false
+++

logand.app-v2 F-559: a broad integration lease blocked three tickets for 30+ minutes over a generated file and an append-only file.
