+++
id = "01M702DP1KM3KCXS9ATGAV73BF"
title = "Grimble LOG: track handle-flow and non-literal mode_arg in U witness"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-09T11:52:13Z"
updated = "2026-11-09T12:12:02Z"
scope = ["crates/grimble-check/src/log/universal.rs", "docs/design/grimble/output-atoms.md"]

[[acceptance]]
text = "A name bound once in the file (fd = 1, h = sys.stdout) is followed one hop when it is a call argument; a rebound name is not"
bound = true

[[acceptance]]
text = "Calls whose mode_arg is neither a literal nor a once-bound name are listed by mode_unresolved_calls"
bound = true
+++
