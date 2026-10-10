+++
id = "01M4GKAYSGHAE5QAXN1BJBTQN2"
title = "Bulk ticket read: ticket list --full (or export) emits every ticket with aliases and events in one call"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T15:08:35Z"
updated = "2026-10-10T21:04:53Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-ledger/**", "crates/frob/**", "changelog.d/**", "docs/design/cli.md"]

[[acceptance]]
text = "Given 451 tickets, when frob ticket list --full --json runs, then every ticket with its aliases and events is emitted in one call within a few seconds"
bound = true
+++

logand.app-v2 F-550: one show per ticket took 40-50 s.
