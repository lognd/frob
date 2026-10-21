+++
id = "01M5ED173QYA7JQPTCNKZJGSQD"
title = "mirror: MirrorHost must override RunHost::ledger_commits so the watermark advances"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:55:37Z"
updated = "2026-10-21T06:07:17Z"
scope = ["crates/frob-mirror/src/host.rs", "crates/frob-mirror/tests/host.rs"]

[[acceptance]]
text = "A clean mirror pass over a ledger with commits advances the watermark to the log head"
bound = true
+++

Follow-up from ~E70J6TS; host.rs does not override the default empty ledger_commits.
