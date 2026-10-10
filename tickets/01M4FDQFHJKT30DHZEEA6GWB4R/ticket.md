+++
id = "01M4FDQFHJKT30DHZEEA6GWB4R"
title = "Retroactive closeout: record evidence and close a ticket outside any active cycle without a lease, with a reason, excluded from the current sprint's commitment"
type = "story"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T04:11:19Z"
updated = "2026-10-10T21:14:17Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-pm/**", "crates/frob-evidence/**", "crates/frob/**", "changelog.d/**", "docs/reference/cli/frob.md", "docs/design/cli.md"]

[[acceptance]]
text = "Given a ticket from a closed cycle, when frob ticket closeout runs with evidence and --reason, then the ticket closes done with the evidence, no lease is taken, and the active cycle's commitment and over-commit stats are unchanged"
bound = true
+++
