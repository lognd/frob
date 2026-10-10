+++
id = "01M4GKBXQS0VY1PWG3B6QH12NZ"
title = "frob check --timing prints nothing; per-stage timings exist only in .frob/telemetry.jsonl"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T15:09:07Z"
updated = "2026-10-10T21:56:53Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-check/**", "crates/gob-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given frob check --timing, when it finishes, then a per-stage and per-rule timing table is printed (text) or included under data.timing (json)"
bound = false
+++

logand.app-v2 F-553.
