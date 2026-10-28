+++
id = "01M56M6YM7DZTNXT65BP75ES1Y"
title = "Per-command Session part 2: open worktree and ratchet checkout once in frob-check/gob-git, share a Session across frob CLI verbs, one Workspace type (audit M14)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-18T04:27:10Z"
updated = "2026-10-28T12:55:58Z"
labels = ["no-story"]
scope = ["crates/frob-check/**", "crates/gob-git/**", "crates/frob/**", "crates/frob-evidence/**", "crates/frob-worktree/**"]
+++

found while working ~R1VFD4X: land opens the primary checkout once (test land_opens_each_repository_once) but the ticket worktree is still discovered about 14 times and the ratchet land-checkout about 11 (frob-check memo/snapshot/scope, gob-git fallback/content, frob-release config); frob CLI verbs still call Located::discover per helper; three Workspace types remain.

no-story: internal engineering task in frob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
