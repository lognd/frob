+++
id = "01M71T80ZZPW5Z00CKF3ANQ2X3"
title = "crunk host runs GRL: gob-plan bridge for stamped files, ORG001/003/004/005, retire Rust duplicates (follow-up of NBAN5SY)"
type = "task"
category = "todo"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-11-10T04:07:48Z"
updated = "2026-11-10T16:22:04Z"
scope = ["crates/gob-plan/**", "changelog.d/*.added.md", "docs/**"]

[[acceptance]]
text = "gob-plan Input/Relations bridge builds file nodes with attrs plus config.layers and config.org tables from StampedFile"
bound = false

[[acceptance]]
text = "generated GRL modules LAYER001 and ORG002 run from the crunk host"
bound = false

[[acceptance]]
text = "ORG001/ORG005 glob membership over side columns, ORG003 component-prefix test, ORG004 via file.bucket"
bound = false

[[acceptance]]
text = "retire Rust ORG001-005, LAYER001, ORG002 duplicates in crunk-rules"
bound = false
+++
