+++
id = "01M4P2N1M00A5XSDA8SW5FBRR8"
title = "agent: frob agent brief (compact ticket/lease/worktree context for SessionStart)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:26Z"
updated = "2026-10-24T04:25:35Z"
scope = ["crates/frob-cli/**", "crates/frob/**"]

[[acceptance]]
text = "brief prints a bounded summary of the active ticket, lease scope, worktree and standing rules"
bound = true

[[acceptance]]
text = "output is capped at a configured byte budget"
bound = true
+++
