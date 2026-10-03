+++
id = "01M4069RJJ4C73Z6GKKSV1E7PS"
title = "PM034 milestone-member-outside-epics (Warning)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T07:48:02Z"
idempotency_key = "m2-rel-pm034"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/rules/membership.rs", "docs/reference/rules/pm/**", "crates/frob-pm/src/rules/**", "crates/frob-pm/src/lib.rs", "crates/frob-pm/Cargo.toml", "crates/frob-pm/tests/**", "crates/frob-check/Cargo.toml"]

[[links]]
kind = "blocked-by"
target = "01M4069R5RH6KRMMNQA76XZ8VG"

[[acceptance]]
text = "Given a ticket labelled for a milestone whose epic chain misses the milestone's epics, when frob check runs, then PM034 names it"
bound = false

[[acceptance]]
text = "Given a ticket under a member epic, when frob check runs, then PM034 is silent"
bound = false
+++

Tickets carrying the milestone (through label release:VERSION during bootstrap, through the epic afterwards) whose parent chain does not reach one of the milestone's epics fire PM034, the v1 T-5149 failure.
