+++
id = "01M70SK0DAGN0D4YF323K1AD1Y"
title = "crunk host stamps GRL relations and LAYER/ORG rules move to crunk-core GRL"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-09T18:37:05Z"
updated = "2026-11-09T19:08:42Z"
scope = ["packs/crunk-core/**", "crates/crunk-rules/**", "design/model.grmb", "crates/gob-plan/src/check/names.rs", "docs/design/shared/rules.md"]
+++

Remaining from ~474HWJV: the crunk host must stamp the relations GRL reads (spec, stylesheet index, file.bucket, file.component), add glob membership over config side columns, then port LAYER001 and ORG001-005 to packs/crunk-core/rules/*.grl, list them in provides.rules, own packs/crunk-core/generated/** in design/model.grmb and drop their exceptions.toml entries.
