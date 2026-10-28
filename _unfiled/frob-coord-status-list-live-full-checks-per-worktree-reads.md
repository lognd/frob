+++
id = "01M5B6QR4JZ19YAGB7922H0R69"
title = "frob coord status: list live full checks per worktree (reads .frob/check.lock)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T23:07:52Z"
updated = "2026-10-28T12:55:41Z"
labels = ["no-story"]
scope = ["crates/frob/**"]
+++

Follow-up of ~F6YXYRZ item (3): the lock file .frob/check.lock (pid, started, argv) now exists; the coord verb (T-5784) does not exist yet in the Rust tree. Surface live holders per worktree.

no-story: internal engineering task in frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
