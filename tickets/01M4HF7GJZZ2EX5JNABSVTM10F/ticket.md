+++
id = "01M4HF7GJZZ2EX5JNABSVTM10F"
title = "Landed worktrees renamed to <name>.removing are never deleted: the background removal thread dies with the land process and the next land does not sweep leftovers (36 GB accumulated in one afternoon)"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-09T23:16:02Z"
updated = "2026-10-10T02:14:17Z"
labels = ["creates:crates/frob-worktree/src/gc/removing.rs"]
scope = ["changelog.d/**", "crates/frob-worktree/src/gc/pass.rs", "crates/frob-worktree/src/gc/mod.rs", "crates/frob-worktree/tests/gc.rs", "crates/frob-worktree/src/gc/removing.rs"]

[[acceptance]]
text = "Given a land whose process exits before its background removal finishes, when the next land or frob gc runs, then every unregistered <worktree-dir>/*.removing directory is deleted, and frob doctor reports any that remain"
bound = true
+++

2026-10-09: 11 *.removing dirs (36 GB) remained in ../frob-v2-wt after queue lands; host C: drive fell from 306 GB to 142 GB free. Introduced by ~8J3BE8W; removed by hand.
