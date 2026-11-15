+++
id = "01M7EX7ZWE0ZE9PDFBC6RY4M0Q"
title = "land lock: re-verify the holder before taking over a stale lock"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:10:20Z"
updated = "2026-11-15T06:10:20Z"
labels = ["no-story"]

[[acceptance]]
text = "Takeover aborts if the lock content changed between staleness check and replace (test)"
bound = false

[[acceptance]]
text = "Two concurrent takeovers: exactly one wins (test)"
bound = false
+++

Source: frob-audit-core.md M2. Evidence: crates/frob-land/src/lock.rs:450-518 takeover replaces the lock file without re-reading and re-checking the holder, racing a live holder that refreshed it. Remedy: compare-and-swap on the holder token (re-read, verify unchanged and dead/stale, then replace). Files: crates/frob-land/src/lock.rs.
