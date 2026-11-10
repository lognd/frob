+++
id = "01M7179W20SP4SF3GP0G32HAM7"
title = "Refresh: push_wip of claimed ticket branches, plus e2e test for post-merge page regeneration"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T22:36:45Z"
updated = "2026-11-10T03:26:02Z"
scope = ["crates/frob-worktree/**", "crates/frob/src/**", "crates/frob/tests/**", "crates/frob-ledger/src/**", "docs/**", "changelog.d/01M7179W20SP4SF3GP0G32HAM7.added.md"]
+++

Split from ~7WV749G. (1) Add [sync] push_wip (default true) and push this clone's claimed ticket/<handle> branches as WIP in refresh (design doc 5.2 step 4), never auto-merging code. (2) Add an end-to-end test of regenerate_pages after a Merged ledger integrate in an orphan-layout two-clone setup.
