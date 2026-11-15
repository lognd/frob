+++
id = "01M7EXR1ZFYCMPATX0V581X6YJ"
title = "land cost telemetry and unique stage names"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:07Z"
updated = "2026-11-15T06:19:07Z"
labels = ["no-story"]

[[acceptance]]
text = "Each land records per-stage cost (test)"
bound = false

[[acceptance]]
text = "Stage names are unique (test)"
bound = false
+++

Source: frob-audit2-repo.md M8/F6. Evidence: frob.toml:28,38,48 stage names collide; land cost unrecorded. Remedy: unique names and a land-cost ledger. Files: frob.toml, timing code.
