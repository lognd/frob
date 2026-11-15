+++
id = "01M7EXR0RS8FN7630RWM8R8J20"
title = "claim push uses its own timeout rather than the 2.5 s probe timeout"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:05Z"
updated = "2026-11-15T06:19:06Z"
labels = ["no-story"]

[[acceptance]]
text = "Slow push beyond 2.5 s succeeds (test)"
bound = false
+++

Source: frob-audit2-repo.md M2/F10. Evidence: crates/frob-worktree/src/claim.rs:50-190. Remedy: configurable push timeout with retry. Files: claim.rs.
