+++
id = "01M6D8GGCG31HRTYK4SGB5GKJM"
title = "frob land from inside a worktree fails E-INTERNAL writing land.lock.holder via .git/worktrees/<id>/../../frob path (merge still lands)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T04:33:03Z"
updated = "2026-11-02T05:31:15Z"
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "Acquiring the land lock through a linked-worktree common dir (with .. segments) writes the holder sidecar successfully and the paths resolve to the real common git dir"
bound = true
+++
