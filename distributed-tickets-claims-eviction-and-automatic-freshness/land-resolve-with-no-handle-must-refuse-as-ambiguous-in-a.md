+++
id = "01M5ED9XX1V96EW1F9J9ZK069N"
title = "land: resolve with no handle must refuse as ambiguous in a series worktree holding several leases"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:00:23Z"
updated = "2026-10-21T06:34:34Z"
scope = ["changelog.d/01M5ED9XX1V96EW1F9J9ZK069N.fixed.md", "crates/frob-land/src/land.rs"]

[[acceptance]]
text = "land with no handle refuses E-LAND-AMBIGUOUS when the cwd worktree holds several live leases"
bound = true
+++

Follow-up from ~P2W1WMP.
