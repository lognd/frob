+++
id = "01M4VNXV7VSDWPPT76YEKGVRT7"
title = "cycle plan --apply: call PmStore::assign_many once instead of assign_one per ticket"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-13T22:25:24Z"
updated = "2026-10-28T12:55:52Z"
labels = ["no-story"]
scope = ["crates/frob/**"]

[[links]]
kind = "blocked-by"
target = "01M4DPJJ8J8C8VP9H6EDJG6B4Z"

[[acceptance]]
text = "Given plan --apply assigning N tickets, when run via the CLI, then one commit is written"
bound = false
+++

found while working ~DJG6B4Z. PmStore::assign_many now exists; wire crates/frob/src/cycle_cmd.rs plan --apply to collect picks into (TicketId, moved_from) and call it once (over-commit bodies via the over_commit arg).

no-story: internal engineering task in frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
