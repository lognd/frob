+++
id = "01M7D2VCMWZGRRNV16CGETJFHC"
title = "Fix snapshot and trybuild drift after Effects capability landed"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-14T13:09:50Z"
updated = "2026-11-14T13:38:50Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/tests/**", "crates/gob-macros/tests/**", "changelog/**"]

[[acceptance]]
text = "The measured matrix snapshots and ui_rule_attr cases match the Effects capability, so CI is green"
bound = true
+++

CI on experimental fails measured matrix snapshots, web_corpus capability matrix snapshot, and ui_rule_attr after T28A73Q flipped effects cells to Implemented syntactic.
