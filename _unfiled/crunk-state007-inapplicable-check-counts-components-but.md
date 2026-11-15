+++
id = "01M7FEY1PK1BYRQ7MFY4FNJYCY"
title = "crunk STATE007: inapplicable check counts components but subjects count only screens (fires on component-only project)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T11:19:29Z"
updated = "2026-11-15T11:41:46Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/src/rules/state007.rs"]

[[acceptance]]
text = "Given a project with components but no screens, when STATE007 is evaluated, then it is reported inapplicable rather than firing"
bound = false
+++
