+++
id = "01M4069REJDB8FFVZFMJWAAVRY"
title = "PM001 and PM002: milestone goal and epic completeness rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T16:50:04Z"
idempotency_key = "m2-rel-pm001-002"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/rules/milestone.rs", "docs/reference/rules/pm/**", "crates/frob-pm/src/rules/mod.rs", "crates/frob-pm/tests/corpus.rs", "crates/frob-pm/tests/mdtest/pm001.md", "crates/frob-pm/tests/mdtest/pm002.md", "crates/frob-check/src/product.rs", "docs/reference/rules/PM001.md", "docs/reference/rules/PM002.md", "docs/reference/rules/README.md", "crates/frob-pm/src/rules/membership.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069R5RH6KRMMNQA76XZ8VG"

[[acceptance]]
text = "Given a milestone with no goal, when frob check runs, then PM001 fires"
bound = true

[[acceptance]]
text = "Given a milestone with no epics, when frob check runs, then PM002 fires"
bound = false
+++

Rules per pm-enforcement.md 7: PM001 milestone without goal or criteria (unscheduled allowed), PM002 milestone without epics or with a member epic that is itself done-with-open-children. Warn in a fresh repo, Error under [pm] strict.
