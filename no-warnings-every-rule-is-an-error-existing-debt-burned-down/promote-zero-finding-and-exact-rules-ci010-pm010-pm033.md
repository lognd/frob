+++
id = "01M5XMJJTFNZP3FWP3WXK1MB0D"
title = "Promote zero-finding and exact rules (CI010, PM010, PM033, SYS008) to Error"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:03Z"
updated = "2026-10-29T05:15:25Z"
labels = ["no-story"]
scope = ["crates/*/src/**/rules*", "crates/frob-pm/src/legacy/cycle_plan.rs", "crates/*/src/rules/*.md", "crates/grimble-ci/src/lib.rs"]

[[acceptance]]
text = "Every zero-finding Warn/Advisory rule is Error with no baseline; CI010, PM010, PM033, SYS008 fixed then Error"
bound = true

[[acceptance]]
text = "Per-rule counts from a full frob check recorded in the ticket"
bound = true
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.7 steps 2-3). Filed from ~ZHW5Y2M.

no-story: internal engineering task in crates/*/src/**/rules*; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
