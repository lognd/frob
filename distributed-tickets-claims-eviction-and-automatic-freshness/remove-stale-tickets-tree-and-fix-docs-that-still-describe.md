+++
id = "01M5XEHYB2ZF4C9CP6ME38P5GG"
title = "Remove stale tickets/ tree and fix docs that still describe the in-tree ledger"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-27T01:10:50Z"
updated = "2026-10-27T02:12:37Z"
scope = ["tickets/**", ".gitattributes", "README.md", "CONTRIBUTING.md", "docs/**"]

[[acceptance]]
text = "tickets/ is removed from experimental and .gitattributes no longer references it"
bound = false

[[acceptance]]
text = "README, CONTRIBUTING and docs guides/design/migration pages describe the frob-tickets orphan ledger (.events layout), keeping tickets/ only where describing v1 or legacy migration"
bound = false
+++

Owner approved removal. Verified ticket verbs work without tickets/ (list, doable). Run full frob check in a scratch worktree first.
