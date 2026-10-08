+++
id = "01M4CXTP6NCCZ7YNQCER0RXNYF"
title = "land ledger_step idempotent after a partial failure (append_land succeeded, close failed): no duplicate land event on retry"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T04:54:58Z"
updated = "2026-10-08T04:54:58Z"
scope = ["changelog.d/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given a land whose close failed after append_land, when the close is retried, then exactly one land event exists"
bound = false
+++

Follow-up from ~BWMVSPZ.
