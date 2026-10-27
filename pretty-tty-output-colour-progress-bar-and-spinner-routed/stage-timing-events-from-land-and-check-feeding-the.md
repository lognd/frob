+++
id = "01M5XMN8N235JFVMJW9MCY59H4"
title = "Stage timing events from land and check feeding the presenter and a profile report"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-10-27T02:57:31Z"
updated = "2026-10-27T05:05:43Z"
scope = ["crates/frob-land/**", "crates/frob-present/**", "crates/frob-check/**", "docs/**", "crates/frob/src/check_view.rs"]

[[acceptance]]
text = "frob land and frob check emit per-stage start/finish events with durations to the presenter; a --profile or stats view reports per-command stage timings"
bound = true
+++
