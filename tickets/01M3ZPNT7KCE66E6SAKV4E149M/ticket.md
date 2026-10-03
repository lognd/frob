+++
id = "01M3ZPNT7KCE66E6SAKV4E149M"
title = "G12 follow-ups: one walk for check and ack, mandatory ack reason, rename log and knobs"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T01:39:51Z"
updated = "2026-10-03T02:20:58Z"
idempotency_key = "m2-g12-followups"
labels = ["milestone:2"]
scope = ["crates/grimble-bind/**", "crates/grimble-check/**", "crates/grimble/**", "crates/gob-lock/**", "docs/reference/**", "Cargo.lock"]

[[acceptance]]
text = "Given the workspace, when grepped for the walk logic, then grimble ack and grimble check call one function, and grimble ack without --reason is a usage error"
bound = false
+++

From ~T9R1B70: grimble ack copied the walk logic of grimble_check::survey because grimble-check was leased; expose one shared function and delete the copy. binding.md 5.3 makes --reason mandatory for grimble ack: enforce it (E-USAGE with remedy). Record a kind=rename entry in the ack log (binding.md 5.5 item 1). Read rename_min_tokens from the [grimble] table instead of a constant. Add the shape_contract to the gob-lock FlowEnd so SYS006 can honour versioning compat=backward (binding.md 5.2, 6.6).
