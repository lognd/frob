+++
id = "01M7EX85HW539YDYZ64F58PM80"
title = "mirror lock: add a heartbeat so a live long run is not taken over"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:10:26Z"
updated = "2026-11-15T06:10:26Z"
labels = ["no-story"]

[[acceptance]]
text = "A refreshed lock is not stale after the age window (test)"
bound = false
+++

Source: frob-audit-core.md L8 (latent). Evidence: crates/frob-mirror/src/lock.rs has no heartbeat; staleness is by age only. Remedy: periodic refresh and age-plus-liveness check. Files: crates/frob-mirror/src/lock.rs.
