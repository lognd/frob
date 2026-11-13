+++
id = "01M5EF4A7DQJQ2SHXYAYCAB73X"
title = "crunk: STATE004 render-ledger coverage per platform"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-11-13T09:40:44Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/**", "docs/design/crunk/**", "docs/reference/rules/**", "docs/README.md"]

[[acceptance]]
text = "Given a screen state without a render entry for a platform, when checked, then STATE004 fires"
bound = true
+++

found while working ~60E2DXH: each screen state needs a render-ledger entry per platform; needs render output.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
