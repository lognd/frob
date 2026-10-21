+++
id = "01M5EF4A7DQJQ2SHXYAYCAB73X"
title = "crunk: STATE004 render-ledger coverage per platform"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-10-21T05:32:16Z"
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given a screen state without a render entry for a platform, when checked, then STATE004 fires"
bound = false
+++

found while working ~60E2DXH: each screen state needs a render-ledger entry per platform; needs render output.
