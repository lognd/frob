+++
id = "01M6C9121R0T8SN5HVJ6R1VZZD"
title = "Stop grimble exceptions/matrix/serve writing .grimble state"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T19:22:51Z"
updated = "2026-11-01T20:57:45Z"

[[acceptance]]
text = "Read-only grimble views leave the repo with no new .grimble files"
bound = true
+++

Follow-up of MPWW9VP: grimble exceptions (crates/grimble/src/exceptions.rs:38), matrix (matrix_cmd.rs:64) and grimble-serve (lib.rs:34) call grimble_check::run with default options and write telemetry.jsonl and precision-history.json. Set skip_telemetry for read-only views; check grimble-ci verbs and .grimble/cache writes too.
