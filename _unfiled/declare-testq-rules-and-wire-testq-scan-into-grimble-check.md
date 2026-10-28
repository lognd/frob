+++
id = "01M5HJNE91SN4N0MR8GHM30Z1Y"
title = "Declare TESTQ rules and wire testq::scan into grimble-check"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T10:31:46Z"
updated = "2026-10-28T12:55:55Z"
labels = ["no-story"]
scope = ["crates/grimble-lints/src/rules/**", "crates/grimble-check/**"]
+++

Found while working ~DJ4K8YD. Detector grimble_lints::testq::scan exists; still needed: rule declarations (TESTQ003 default-off) and a test-pass analogue of time_pass mapping Unknown to Unresolved.

no-story: internal engineering task in grimble-lints; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
