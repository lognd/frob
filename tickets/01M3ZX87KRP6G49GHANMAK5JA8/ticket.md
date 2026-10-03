+++
id = "01M3ZX87KRP6G49GHANMAK5JA8"
title = "PM031 good-first-incomplete and the frob-pm crate"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-03T03:34:46Z"
idempotency_key = "m2-nav-pm031"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-pm/**"]

[[acceptance]]
text = "Given a good-first ticket of 5 points or without a Start here section, when check runs, then PM031 fires naming the missing part"
bound = false

[[acceptance]]
text = "Given a complete good-first ticket, when check runs, then no PM031 is emitted"
bound = false
+++

Implements navigation.md section 4.2; pm-enforcement.md; boundaries.md (frob-pm).

Error on the label: a ticket labelled good-first must have at most [tickets] good_first_max_points (default 2), a scope, Given/When/Then acceptance and a `## Start here` section. Creates the frob-pm crate with this first PM rule (the crate is otherwise milestone 2 or later).
