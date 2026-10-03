+++
id = "01M416Z11V5GR012FR47HWFTBP"
title = "frob-worktree WIP check should count via frob_pm::rules::wip::in_progress"
type = "chore"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T15:43:45Z"
updated = "2026-10-03T15:43:45Z"
scope = ["crates/frob-worktree/src/wip.rs"]
+++

found while working ~ED96MPY: the in-progress listing in frob-worktree wip::check duplicates frob_pm::rules::wip::in_progress; swap it in. Blocked on the ZQRNCXY lease over crates/frob-worktree/**.
