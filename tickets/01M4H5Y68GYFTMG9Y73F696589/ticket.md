+++
id = "01M4H5Y68GYFTMG9Y73F696589"
title = "WIP counts only work in progress: a ticket with passing evidence and a clean check --ticket moves to a ready-to-land column with its own limit, not counted in [pm.wip] in_progress"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-09T20:33:40Z"
updated = "2026-10-17T08:25:07Z"
scope = ["crates/frob-pm/**", "crates/frob-lease/**", "crates/frob-evidence/**", "changelog.d/**", "crates/frob/**", "crates/frob-worktree/**", "docs/**", "crates/frob-check/src/product.rs", "frob.toml"]

[[acceptance]]
text = "Given 16 tickets of which 9 are finished (passing evidence, clean check --ticket) and waiting to land, when another agent runs frob work, then it is admitted because in_progress counts only the 7 being worked; the 9 show in a ready-to-land column (board) with an optional [pm.wip] ready limit"
bound = true
+++

2026-10-09: with lands serial, finished tickets held the 16 WIP slots and idle agents polled for an hour. Kanban practice separates the review/ready column limit from the in-progress limit.
