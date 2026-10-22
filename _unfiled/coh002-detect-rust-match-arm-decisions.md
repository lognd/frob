+++
id = "01M5HJ07B6E0NZ47RCV0HWZR5Y"
title = "COH002: detect Rust match-arm decisions"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T10:20:11Z"
updated = "2026-10-22T10:20:11Z"
scope = ["crates/grimble-check/**", "docs/**"]
+++

match arms fold as a Group of pattern binds under an expression_statement, so match decisions are not detected.
