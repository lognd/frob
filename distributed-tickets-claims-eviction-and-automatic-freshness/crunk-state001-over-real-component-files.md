+++
id = "01M5EF4AC7V53WKDZXV4CZ4F62"
title = "crunk: STATE001 over real component files"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-10-27T02:58:35Z"
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given a component file lacking required states, when checked, then STATE001 fires"
bound = false
+++

found while working ~60E2DXH: STATE001 currently checks screen spec files only; extend to component source files.
