+++
id = "01M4H8NECMX7XBS1J6FDWRJEZV"
title = "frob-land share_build_dir writes the shared target symlink through a worktree's git dir (.git/worktrees/<T>/../../frob/land-target); it dangles once that worktree is removed and cargo stages fail with 'Not a directory'"
type = "bug"
category = "todo"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-09T21:21:19Z"
updated = "2026-10-09T21:21:19Z"
scope = ["crates/frob-land/src/ratchet.rs", "changelog.d/**"]

[[acceptance]]
text = "Given a land run from a ticket worktree that is later removed, when the next land reuses the base checkout, then its target symlink resolves (absolute path to the common dir's frob/land-target, canonicalized), and an existing dangling link is repaired"
bound = false
+++

Found 2026-10-09 after ~8J3BE8W: .git/frob/land-checkout/target -> .git/worktrees/G17RK4A/../../frob/land-target dangled after G17RK4A's worktree was removed; repaired by hand.
