+++
id = "01M7D2VCMWZGRRNV16CGETJFHC"
title = "Fix snapshot and trybuild drift after Effects capability landed"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-14T13:09:50Z"
updated = "2026-11-14T13:10:02Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/tests/**", "crates/gob-macros/tests/**", "changelog/**"]
+++

CI on experimental fails measured matrix snapshots, web_corpus capability matrix snapshot, and ui_rule_attr after T28A73Q flipped effects cells to Implemented syntactic.
