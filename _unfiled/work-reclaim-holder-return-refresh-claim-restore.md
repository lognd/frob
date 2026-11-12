+++
id = "01M5DFKY6K8AH7K75XGTQMVAVA"
title = "work --reclaim, holder-return refresh, claim restore"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T20:21:34Z"
updated = "2026-11-12T15:51:30Z"
labels = ["no-story"]
scope = ["crates/frob-worktree/**", "crates/frob/src/**", "docs/**", "changelog.d/**"]

[[acceptance]]
text = "frob work --reclaim uses reclaim_plan to take over an evicted claim"
bound = true

[[acceptance]]
text = "holder-return refresh wired via holder_return"
bound = true

[[acceptance]]
text = "frob claim restore verb exists and is documented"
bound = true
+++

found while working ~6CVW7F9: wire reclaim_plan and holder_return; add frob claim restore
