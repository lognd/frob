+++
id = "01M4GWKEMB266C6GTFEP4R3G7W"
title = "Repository-wide limits ([pm.wip], [lease], [pm] sprint gate) are read from the worktree's own frob.toml, so a branch cut before a config change keeps enforcing the old values"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T17:50:30Z"
updated = "2026-10-10T21:26:01Z"
scope = ["crates/frob-pm/**", "crates/frob-lease/**", "crates/gob-config/**", "changelog.d/**", "crates/frob-worktree/src/verbs.rs", "crates/frob-worktree/tests/work.rs", "docs/design/pm-enforcement.md"]

[[acceptance]]
text = "Given [pm.wip] in_progress raised on the base branch and a ticket worktree branched before that change, when frob work or a lease operation runs in that worktree, then the repository-wide limits come from the base branch (or the ledger ref) config, not the worktree copy; per-worktree code config stays per worktree"
bound = true
+++

2026-10-09: ~3AP1RKR raised the cap 10 -> 16 on experimental; agents in older worktrees kept getting E-WIP-REPO at 10 until they rebased.
