+++
id = "01M43BEAR3MSMEANKENBQ1KDT7"
title = "v1 importer: merge into an existing ledger and import open tickets as triage"
type = "task"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T11:40:29Z"
updated = "2026-10-04T12:13:42Z"
scope = ["crates/gob-dev/src/import_v1.rs", "crates/gob-dev/src/import_v1/**", "crates/gob-dev/tests/import_v1.rs", "docs/design/migration.md", "crates/gob-dev/src/main.rs"]

[[acceptance]]
text = "Given an existing ledger, when the importer runs with --merge, then it adds only new ticket directories and refuses on any id or alias collision without writing"
bound = true

[[acceptance]]
text = "Given --open-category triage, when open v1 tickets import, then their create events place them in triage"
bound = true
+++
