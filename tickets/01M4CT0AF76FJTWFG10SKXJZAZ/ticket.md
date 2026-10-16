+++
id = "01M4CT0AF76FJTWFG10SKXJZAZ"
title = "PM008 and PM009: ticket aging per category and unsized ticket in ready"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-08T03:48:09Z"
updated = "2026-10-16T00:40:23Z"
scope = ["crates/frob-pm/**", "crates/frob-cli/**", "crates/frob/**", "docs/design/pm-enforcement.md", "changelog.d/**", "crates/frob-check/**", "docs/reference/**", "docs/schemas/**", "docs/design/architecture.md"]

[[acceptance]]
text = "Given a ticket in progress longer than max_age_days, when frob check runs, then PM008 fires with the age"
bound = true

[[acceptance]]
text = "Given a ready ticket with no points, when frob check runs, then PM009 fires"
bound = true
+++

Designed in pm-enforcement.md, not implemented. PM008 fires past [pm] max_age_days per category (in_progress default 3, review 2, ready 30); PM009 a ready ticket without points.
