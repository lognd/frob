+++
id = "01M70VN3RSMK4QGY4XCNBAN5SY"
title = "crunk pipeline executes GRL: stamp spec, stylesheet index, file.bucket, file.component; port ORG001/003/004/005"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-09T19:13:11Z"
updated = "2026-11-10T04:02:56Z"
outcome_text = "Host stamping bridge, ORG001/003/004/005 GRL ports, and retiring the Rust duplicates in crunk-rules."
scope = ["crates/crunk-rules/**", "packs/crunk-core/**", "crates/crunk-ingest/**", "crates/crunk/**"]
+++

Follow-up of ~3K1AD1Y: LAYER001 and ORG002 are GRL; the crunk host does not yet run generated modules. Needs a gob-plan Input/Relations bridge from CrunkHost (config.layers, config.org tables, file.bucket, file.component), glob membership over side columns for ORG001/ORG005, component-prefix test for ORG003, ORG004 via file.bucket, then retire the Rust duplicates.
