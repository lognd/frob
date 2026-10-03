+++
id = "01M4069REJDB8FFVZFMJWAAVRY"
title = "PM001 and PM002: milestone goal and epic completeness rules"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T15:28:18Z"
idempotency_key = "m2-rel-pm001-002"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/rules/milestone.rs", "docs/reference/rules/pm/**"]

[[links]]
kind = "blocked-by"
target = "01M4069R5RH6KRMMNQA76XZ8VG"

[[acceptance]]
text = "Given a milestone with no goal, when frob check runs, then PM001 fires"
bound = false

[[acceptance]]
text = "Given a milestone with no epics, when frob check runs, then PM002 fires"
bound = false
+++

Rules per pm-enforcement.md 7: PM001 milestone without goal or criteria (unscheduled allowed), PM002 milestone without epics or with a member epic that is itself done-with-open-children. Warn in a fresh repo, Error under [pm] strict.
