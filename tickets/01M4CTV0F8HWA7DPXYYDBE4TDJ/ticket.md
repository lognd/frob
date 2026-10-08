+++
id = "01M4CTV0F8HWA7DPXYYDBE4TDJ"
title = "frob.toml unknown keys: one policy for init, doctor and check; work --here gets a base to diff against"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:43Z"
updated = "2026-10-08T04:02:43Z"
scope = ["changelog.d/**", "crates/gob-config/**", "crates/frob-worktree/**", "crates/frob/**"]

[[acceptance]]
text = "Given an unknown key, when init, doctor and check run, then all three report it the same way"
bound = false

[[acceptance]]
text = "Given work --here on a fresh ticket, when check --ticket runs after a change, then the change is in the diff"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md MEDIUM: init refuses an unknown key while doctor and check warn; work --here leaves check --ticket and test --base main with an empty diff on main.
