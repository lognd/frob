+++
id = "01M4CT036SCVJMN2E3GHDTYDAJ"
title = "PM010-PM012: cycle over capacity, cycle without goal, not-ready cycle members"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-08T03:48:01Z"
updated = "2026-10-08T03:48:01Z"
scope = ["crates/frob-pm/**", "crates/frob-cli/**", "crates/frob/**", "docs/design/pm-enforcement.md", "changelog.d/**"]

[[acceptance]]
text = "Given a cycle over its capacity, when frob check runs, then PM010 fires (Advisory) with committed and capacity"
bound = false

[[acceptance]]
text = "Given a cycle with an empty goal, when frob check runs, then PM011 fires"
bound = false

[[acceptance]]
text = "Given a cycle member failing ready_requires, when frob check runs, then PM012 fires naming the failed predicates"
bound = false
+++

Designed in pm-enforcement.md (section 8 table) but never implemented. PM010 advisory over capacity (capacity_points or velocity once min_history is met), PM011 a cycle with no goal, PM012 a member that fails the definition of ready ([pm] ready_requires).
