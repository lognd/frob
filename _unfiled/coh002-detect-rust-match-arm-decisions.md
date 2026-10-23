+++
id = "01M5HJ07B6E0NZ47RCV0HWZR5Y"
title = "COH002: detect Rust match-arm decisions"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T10:20:11Z"
updated = "2026-10-23T03:26:16Z"
scope = ["crates/grimble-check/**", "docs/**"]

[[acceptance]]
text = "Given a Rust function whose body branches with a match expression, when COH002 runs, then the match is counted as one decision and its arms effects are judged"
bound = true

[[acceptance]]
text = "Given a Rust function with no match, when COH002 runs, then its decision count is unchanged"
bound = true
+++

match arms fold as a Group of pattern binds under an expression_statement, so match decisions are not detected.
