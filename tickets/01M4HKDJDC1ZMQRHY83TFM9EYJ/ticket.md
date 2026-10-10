+++
id = "01M4HKDJDC1ZMQRHY83TFM9EYJ"
title = "TOOL001 from a tool-stage timeout is reported retryable:false; a timeout is not a deterministic failure and the land refusal should be retryable"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-10T00:29:15Z"
updated = "2026-10-10T03:04:18Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-check/src/tools.rs", "crates/frob-land/src/**", "changelog.d/**"]

[[acceptance]]
text = "Given a land refused only because a tool stage timed out, when the refusal is printed, then retryable is true and the remedy says to re-run (or raise timeout_secs)"
bound = false

[[acceptance]]
text = "Given a tool stage that failed and passes on an immediate rerun (flaky), when land reports it, then the refusal is retryable:true and names the stage as flaky; frob.toml and the stage's own config files count as implicit inputs of every stage (logand F-575)"
bound = false
+++

logand.app-v2 F-574: a coverage stage timed out at 900 s under load 33-39; the land refusal said retryable:false; a plain re-run passed.
