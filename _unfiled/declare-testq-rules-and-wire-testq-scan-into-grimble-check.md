+++
id = "01M5HJNE91SN4N0MR8GHM30Z1Y"
title = "Declare TESTQ rules and wire testq::scan into grimble-check"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T10:31:46Z"
updated = "2026-10-22T10:31:46Z"
scope = ["crates/grimble-lints/src/rules/**", "crates/grimble-check/**"]
+++

Found while working ~DJ4K8YD. Detector grimble_lints::testq::scan exists; still needed: rule declarations (TESTQ003 default-off) and a test-pass analogue of time_pass mapping Unknown to Unresolved.
