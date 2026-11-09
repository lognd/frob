+++
id = "01M5DBVT9HH0MRR30JVCJZYRTY"
title = "Exclude unrecorded remote claims from doable"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:57Z"
updated = "2026-11-09T22:34:52Z"
scope = ["crates/frob/src/ticket/**", "crates/frob/tests/it/**"]
+++

found while working ~46BECG2. Use frob_worktree::claim::remote_claim: doable must skip a ticket when origin has ticket/<handle> though the ledger shows no claim (design 3.3).
