+++
id = "01M4CT13C64KEVBP74G6VCQP1Q"
title = "cycle close --next-goal and --next-days are silently ignored when nothing is carried"
type = "bug"
category = "in-progress"
priority = "low"
points = 1
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-08T03:48:34Z"
updated = "2026-10-09T23:13:04Z"
scope = ["changelog.d/**", "crates/frob/src/cycle_cmd.rs", "crates/frob/tests/cycle.rs"]

[[acceptance]]
text = "Given a close with --next-goal and nothing carried, when it runs, then the next cycle is created with that goal (or the flags are refused), never ignored"
bound = true
+++

2026-10-07: frob cycle close ~VCCMDF6 --next-goal ... --next-days 2 closed the cycle (all done) and created no next cycle and said nothing. Either create the next cycle from the flags or refuse the flags with a usage error; never drop them silently.
