+++
id = "01M4DPJJW8D3KXZVTEN5D4WN5G"
title = "New worktrees seed their derived cache from the primary's so check --ticket is not a cold whole-repo run"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T12:07:27Z"
updated = "2026-10-08T12:07:27Z"
scope = ["changelog.d/**", "crates/frob-worktree/**", "crates/gob-cache/**"]

[[acceptance]]
text = "Given a warm primary, when frob work creates a worktree and check --ticket runs, then file analysis hits the seeded cache"
bound = false
+++

Follow-up from ~9X572Y1: check --ticket over 10 min in a fresh worktree.
