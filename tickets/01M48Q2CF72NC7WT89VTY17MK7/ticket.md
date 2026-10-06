+++
id = "01M48Q2CF72NC7WT89VTY17MK7"
title = "Token usage hook: per-worktree agent token counts into the activity journal"
type = "task"
category = "todo"
priority = "low"
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:53Z"
updated = "2026-10-06T13:39:53Z"
scope = ["crates/frob-metrics/**", "docs/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q2BWRT117K8E163MWHDN2"

[[acceptance]]
text = "the hook writes counts to the journal in a fixture"
bound = false

[[acceptance]]
text = "stats reports tokens per point when present and says absent otherwise"
bound = false
+++

A documented Claude Code hook (PostToolUse/Stop) that appends token usage per session to the worktree's .frob activity journal, so cost per point can use tokens as well as wall-clock; frob never reads harness transcripts itself. Privacy: counts only, no content.
