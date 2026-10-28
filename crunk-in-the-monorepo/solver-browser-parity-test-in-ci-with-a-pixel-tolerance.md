+++
id = "01M4CXRWBYR6P0WFRW5GBBJGEY"
title = "Solver-browser parity test in CI with a pixel tolerance"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-08T04:53:59Z"
updated = "2026-10-28T12:55:54Z"
labels = ["no-story"]
scope = ["changelog.d/**", "crates/crunk-gallery/**", ".github/workflows/**"]

[[links]]
kind = "blocked-by"
target = "01M5XCWYB9M2YSJ5EGABMREX1B"

[[links]]
kind = "blocked-by"
target = "01M5XCXV74XZTCK4N56B46PAY4"

[[acceptance]]
text = "Given a scene whose solver and browser boxes differ beyond tolerance, when CI runs, then the parity job fails naming the node"
bound = false
+++

docs/design/crunk.md section 3.

no-story: internal engineering task in crunk-gallery; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
