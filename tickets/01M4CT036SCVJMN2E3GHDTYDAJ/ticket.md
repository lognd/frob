+++
id = "01M4CT036SCVJMN2E3GHDTYDAJ"
title = "PM010-PM012: cycle over capacity, cycle without goal, not-ready cycle members"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-08T03:48:01Z"
updated = "2026-10-10T03:34:40Z"
scope = ["docs/design/pm-enforcement.md", "changelog.d/**", "crates/frob-pm/src/cycle/mod.rs", "crates/frob-pm/src/cycle/history.rs", "crates/frob-pm/src/rules/mod.rs", "crates/frob-pm/src/rules/cycle_plan.rs", "crates/frob-pm/tests/corpus.rs", "crates/frob-pm/tests/mdtest/pm01*.md", "crates/frob/src/cycle_cmd.rs", "docs/reference/rules/**", "crates/frob-check/src/product.rs"]

[[acceptance]]
text = "Given a cycle over its capacity, when frob check runs, then PM010 fires (Advisory) with committed and capacity"
bound = true

[[acceptance]]
text = "Given a cycle with an empty goal, when frob check runs, then PM011 fires"
bound = true

[[acceptance]]
text = "Given a cycle member failing ready_requires, when frob check runs, then PM012 fires naming the failed predicates"
bound = true
+++

Designed in pm-enforcement.md (section 8 table) but never implemented. PM010 advisory over capacity (capacity_points or velocity once min_history is met), PM011 a cycle with no goal, PM012 a member that fails the definition of ready ([pm] ready_requires).
