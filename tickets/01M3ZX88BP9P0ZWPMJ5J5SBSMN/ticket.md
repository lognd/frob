+++
id = "01M3ZX88BP9P0ZWPMJ5J5SBSMN"
title = "frob tour: the stops one at a time with next and previous"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:47Z"
updated = "2026-10-12T02:09:04Z"
idempotency_key = "m2-nav-tour-verb"
labels = ["milestone:2", "area:navigation", "creates:crates/frob/src/tour_cmd.rs", "creates:crates/frob/tests/tour.rs"]
scope = ["crates/frob/src/tour_cmd.rs", "crates/frob/src/lib.rs", "crates/frob/src/product.rs", "crates/gob-dev/profile.toml", "docs/reference/**", "docs/schemas/**", "crates/frob/tests/tour.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX887RZB82G8HR5JKQ2FER"

[[acceptance]]
text = "Given `frob tour`, when run on a TTY, then stop 1 shows with next and previous controls"
bound = true

[[acceptance]]
text = "Given a non-TTY, when run, then all stops print in order"
bound = true
+++

Implements navigation.md section 5 (last paragraph).

Same stops in the terminal; opens linked files in the pager.
