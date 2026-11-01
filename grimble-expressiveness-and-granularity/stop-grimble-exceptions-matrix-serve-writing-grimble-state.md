+++
id = "01M6C9121R0T8SN5HVJ6R1VZZD"
title = "Stop grimble exceptions/matrix/serve writing .grimble state"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T19:22:51Z"
updated = "2026-11-01T21:04:25Z"
scope = ["crates/grimble-serve/src/lib.rs", "crates/grimble-serve/tests/serve.rs", "crates/grimble/src/exceptions.rs", "crates/grimble/src/matrix_cmd.rs", "crates/grimble/tests/read_only.rs", "changelog.d/01M6C9121R0T8SN5HVJ6R1VZZD.fixed.md"]

[[acceptance]]
text = "Read-only grimble views leave the repo with no new .grimble files"
bound = true
+++

Follow-up of MPWW9VP: grimble exceptions (crates/grimble/src/exceptions.rs:38), matrix (matrix_cmd.rs:64) and grimble-serve (lib.rs:34) call grimble_check::run with default options and write telemetry.jsonl and precision-history.json. Set skip_telemetry for read-only views; check grimble-ci verbs and .grimble/cache writes too.
