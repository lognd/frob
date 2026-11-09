+++
id = "01M5DBVT9HH0MRR30JVCJZYRTY"
title = "Exclude unrecorded remote claims from doable"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:57Z"
updated = "2026-11-09T22:56:11Z"
scope = ["crates/frob/src/ticket/**", "crates/frob/tests/it/**", "crates/frob-worktree/src/claim.rs", "docs/design/frob/distributed-tickets.md", "changelog.d/01M5DBVT9HH0MRR30JVCJZYRTY.changed.md"]
+++

found while working ~46BECG2. Use frob_worktree::claim::remote_claim: doable must skip a ticket when origin has ticket/<handle> though the ledger shows no claim (design 3.3).
