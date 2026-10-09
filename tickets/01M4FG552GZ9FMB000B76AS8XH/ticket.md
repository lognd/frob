+++
id = "01M4FG552GZ9FMB000B76AS8XH"
title = "Trunk mode on a feature branch: ticket verbs read and write the trunk ref silently; envelope ok contradicts data.ok"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T04:53:45Z"
updated = "2026-10-09T19:00:52Z"
labels = ["adoption:logand-app", "creates:crates/frob/tests/envelope_invariant.rs", "creates:crates/frob/tests/ticket_trunk_notice.rs", "creates:changelog.d/01M4FG552GZ9FMB000B76AS8XH*"]
scope = ["crates/gob-cli/src/command.rs", "crates/frob/tests/envelope_invariant.rs", "crates/frob/tests/ticket_trunk_notice.rs", "changelog.d/01M4FG552GZ9FMB000B76AS8XH*", "crates/gob-cli/src/error.rs", "docs/design/tickets.md", "crates/frob/src/workspace.rs"]

[[acceptance]]
text = "Given [tickets] ref = refs/heads/main and a checkout on a feature branch, when ticket doctor or ticket list runs, then the output says which ref it reads and that the working tree is not the ledger, and a writing verb states it commits to main (or refuses without --to-trunk)"
bound = false

[[acceptance]]
text = "Given any verb whose data.ok is false, when it prints the envelope, then the top-level ok is false too (a test asserts the invariant for every verb)"
bound = false

[[acceptance]]
text = "Given trunk mode where ticket verbs commit ledger-only changes to main, when frob land --dry-run runs, then ledger-only commits on main do not make it report main as not merged (logand F-562)"
bound = false
+++

logand.app-v2 F-504: 0 tickets and 29 TICK004 on old v1 files with envelope ok:true and data.ok false.
