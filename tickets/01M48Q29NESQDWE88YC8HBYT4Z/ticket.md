+++
id = "01M48Q29NESQDWE88YC8HBYT4Z"
title = "frob board --brief: what is being done now, next and blocked"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:50Z"
updated = "2026-10-07T01:25:22Z"
scope = ["crates/frob-pm/src/board.rs", "crates/frob/src/board_cmd.rs", "crates/frob/tests/**"]

[[acceptance]]
text = "text and JSON come from one Board value (test)"
bound = true

[[acceptance]]
text = "an in-progress ticket shows its last observed signal and age from events and git, with no state the agent must set"
bound = true

[[acceptance]]
text = "fits 80 columns for a repository with 5 in-progress tickets (snapshot)"
bound = true
+++

A compact board view for humans and agents: each in-progress ticket with holder, worktree, age, last observed signal (commit, test or evidence run, land) and its time since; then the next doable tickets in dispatch order; then blocked tickets with their blocker. Same Board type as the full board (frob-pm), text and JSON from one value.
