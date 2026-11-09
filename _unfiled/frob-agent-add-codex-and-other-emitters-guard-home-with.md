+++
id = "01M5BN07TWS6HME68083TP038J"
title = "frob agent: add codex and other emitters; guard --home with --agent all"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T03:17:11Z"
updated = "2026-11-09T08:35:21Z"
scope = ["crates/frob/src/agent/**", "crates/frob/src/agent_cmd.rs", "crates/frob/tests/it/agent.rs", "docs/guides/hooks.md", "changelog.d/01M5BN07TWS6HME68083TP038J.*.md"]
+++

Add further emitter modules (one module plus one line in emitters()); once 2+ emitters exist, --home with --agent all must be rejected (already coded, untested). Found while working ~VHZ1FDQ.
