+++
id = "01M7AV38AAVKP80JZ6XEW8J39T"
title = "grimble COH/PATH/ERR/TIME skip non-Rust/Python/TS languages without reporting"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-14T00:29:22Z"
labels = ["no-story"]
scope = ["crates/grimble-*/**"]

[[acceptance]]
text = "Unsupported languages yield an Unresolved finding, not silence."
bound = true
+++

H5: TSX/JS/JSX/Go/Java/C/C#/C++ are silently skipped; emit Unresolved. Source: frob-audit-grimble-crunk.md (Opus audit).
