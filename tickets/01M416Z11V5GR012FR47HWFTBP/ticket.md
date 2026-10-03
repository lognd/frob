+++
id = "01M416Z11V5GR012FR47HWFTBP"
title = "frob-worktree WIP check should count via frob_pm::rules::wip::in_progress"
type = "chore"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T15:43:45Z"
updated = "2026-10-03T16:07:17Z"
scope = ["crates/frob-worktree/src/wip.rs", "crates/frob-pm/src/rules/wip.rs", "crates/frob-pm/tests/mdtest/pm013.md", "crates/frob-worktree/tests/work.rs", "docs/design/pm-enforcement.md"]
+++

found while working ~ED96MPY: the in-progress listing in frob-worktree wip::check duplicates frob_pm::rules::wip::in_progress; swap it in. Blocked on the ZQRNCXY lease over crates/frob-worktree/**.
