+++
id = "01M5EH4JK63Q7HEJ2PZ3A55YQE"
title = "Verify frob land check stages pass CARGO_INCREMENTAL and CARGO_PROFILE_* env through to cargo"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T06:07:22Z"
updated = "2026-10-28T12:55:41Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]
+++

found while working ~P8YV3RW: frob test inherits the caller's cargo env (regression test added). frob land's check stages were not audited (out of scope: frob-land crate); confirm they spawn cargo with an inherited environment and pin it with a test.

no-story: internal engineering task in frob-land; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
