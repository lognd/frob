+++
id = "01M416Z11V5GR012FR47HWFTBP"
title = "frob-worktree WIP check should count via frob_pm::rules::wip::in_progress"
type = "chore"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T15:43:45Z"
updated = "2026-10-03T16:22:49Z"
scope = ["crates/frob-worktree/src/wip.rs", "crates/frob-pm/src/rules/wip.rs", "crates/frob-pm/tests/mdtest/pm013.md", "crates/frob-worktree/tests/work.rs", "docs/design/pm-enforcement.md", "docs/reference/rules/PM013.md", "crates/frob-check/src/product.rs", "crates/frob-pm/tests/corpus.rs"]

[[acceptance]]
text = "PM013 and the work gate share one lease-aware, lane-aware WIP count (frob_pm::rules::wip::count), documented in pm-enforcement.md"
bound = true

[[acceptance]]
text = "The gate and PM013 agree on the same fixture"
bound = true

[[acceptance]]
text = "PM013 mdtest corpus covers expedite exempt, expedite over max, closed lane and stale"
bound = true
+++

found while working ~ED96MPY: the in-progress listing in frob-worktree wip::check duplicates frob_pm::rules::wip::in_progress; swap it in. Blocked on the ZQRNCXY lease over crates/frob-worktree/**.
