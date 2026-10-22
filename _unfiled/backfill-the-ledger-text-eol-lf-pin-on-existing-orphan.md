+++
id = "01M5J931Y2JCF9J0XFVRP71BER"
title = "Backfill the ledger text eol=lf pin on existing orphan ticket branches"
type = "task"
category = "in-progress"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-22T17:03:41Z"
updated = "2026-10-22T17:18:36Z"
scope = ["crates/frob-ledger/**"]

[[acceptance]]
text = "Given an existing orphan ticket branch without the eol pin, when frob doctor or init runs, then the pin is added once and a second run changes nothing"
bound = true
+++

~6EQFB65 pins md and toml to LF only when init_branch creates the branch. Branches created earlier or adopted from origin lack it.
