+++
id = "01M4NX4T2TPAM4RXM43173HKCF"
title = "Start the tool-stage check in the background after each commit in a ticket worktree"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-11T16:36:11Z"
updated = "2026-11-02T11:16:25Z"
scope = ["crates/frob-worktree/**", "changelog.d/**", "docs/**"]

[[acceptance]]
text = "frob work installs a shared post-commit hook that runs frob check --ticket detached only for ticket/* branches of linked worktrees, never replacing a foreign hook"
bound = true
+++

Follow-up of ~3K1MDJD (memo store landed): a post-commit trigger runs frob check --ticket detached so the memo is warm before check/land.
