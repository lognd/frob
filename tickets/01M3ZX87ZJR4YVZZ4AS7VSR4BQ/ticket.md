+++
id = "01M3ZX87ZJR4YVZZ4AS7VSR4BQ"
title = "PM032 good-first-pool-low"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:47Z"
updated = "2026-10-03T03:34:47Z"
idempotency_key = "m2-nav-pm032"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-pm/src/pm032.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX87KRP6G49GHANMAK5JA8"

[[acceptance]]
text = "Given two ready good-first tickets, when check runs, then PM032 warns with the count and the minimum"
bound = false

[[acceptance]]
text = "Given three ready good-first tickets, when check runs, then it does not fire"
bound = false
+++

Implements navigation.md section 4.2.

Warning: fewer than [tickets] good_first_min (default 3) ready good-first tickets.
