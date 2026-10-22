+++
id = "01M5HYTAQEYA72YHZWGHPACR52"
title = "Version-bump awareness for griffe VERSION001 findings"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T14:04:09Z"
updated = "2026-10-22T17:42:16Z"
scope = ["crates/gob-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given a griffe-reported breaking change and a package version bump that permits it, when VERSION001 runs, then no error is raised"
bound = true

[[acceptance]]
text = "Given a griffe-reported breaking change with no version bump, then VERSION001 is an error"
bound = false
+++

found while working BVDP7MK
