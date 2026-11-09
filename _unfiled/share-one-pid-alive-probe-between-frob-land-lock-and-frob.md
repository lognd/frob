+++
id = "01M5B6QRBPJH4J17RJXR3GTHAN"
title = "Share one pid_alive probe between frob-land lock and frob-check concurrent lock"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-19T23:07:53Z"
updated = "2026-11-09T06:14:15Z"
labels = ["no-story"]
scope = ["crates/frob-land/**", "crates/gob-exec/**"]
+++

frob-check::concurrent::pid_alive duplicates frob-land lock.rs pid_alive; extract to a shared crate (found while working ~F6YXYRZ).

no-story: internal engineering task in frob-land; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
