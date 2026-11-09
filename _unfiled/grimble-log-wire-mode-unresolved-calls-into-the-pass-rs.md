+++
id = "01M703GP9HT71SCNKQE291TPE4"
title = "Grimble LOG: wire mode_unresolved_calls into the pass.rs cross-check"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T12:11:20Z"
updated = "2026-11-09T12:45:27Z"
scope = ["crates/grimble-check/src/log/pass.rs", "docs/design/grimble/output-atoms.md"]
+++

mode_unresolved_calls (universal.rs, from ~GAV73BF) lists mode-aware calls with an undecidable mode; report them as LOG001 Unresolved in cross_check.
