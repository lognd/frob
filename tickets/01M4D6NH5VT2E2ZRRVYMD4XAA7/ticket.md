+++
id = "01M4D6NH5VT2E2ZRRVYMD4XAA7"
title = "frob-ack: open the repository-shared cache instead of its own .frob/cache.sqlite"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:27Z"
updated = "2026-10-11T16:41:25Z"
scope = ["changelog.d/**", "crates/frob-ack/**"]

[[acceptance]]
text = "Given a fresh worktree after a warm primary run, when frob ack runs, then it hits the shared cache"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 7 (inputs.rs:147, rules.rs:453).
