+++
id = "01M5EF4A9VM42NW2805KJJ86Q4"
title = "crunk: STATE005 state diff threshold"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-10-21T05:32:16Z"
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given two near-identical state renders, when checked, then STATE005 fires"
bound = false
+++

found while working ~60E2DXH: states must differ from each other by a threshold; needs render output.
