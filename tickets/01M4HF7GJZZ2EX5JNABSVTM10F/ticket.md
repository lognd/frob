+++
id = "01M4HF7GJZZ2EX5JNABSVTM10F"
title = "Landed worktrees renamed to <name>.removing are never deleted: the background removal thread dies with the land process and the next land does not sweep leftovers (36 GB accumulated in one afternoon)"
type = "bug"
category = "todo"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-09T23:16:02Z"
updated = "2026-10-09T23:16:02Z"
scope = ["crates/frob-land/src/land.rs", "crates/frob-worktree/src/gc/**", "changelog.d/**"]

[[acceptance]]
text = "Given a land whose process exits before its background removal finishes, when the next land or frob gc runs, then every unregistered <worktree-dir>/*.removing directory is deleted, and frob doctor reports any that remain"
bound = false
+++

2026-10-09: 11 *.removing dirs (36 GB) remained in ../frob-v2-wt after queue lands; host C: drive fell from 306 GB to 142 GB free. Introduced by ~8J3BE8W; removed by hand.
