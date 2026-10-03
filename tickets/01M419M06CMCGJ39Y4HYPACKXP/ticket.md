+++
id = "01M419M06CMCGJ39Y4HYPACKXP"
title = "One ledger-path classifier shared by frob-check scope and frob-land retry"
type = "chore"
category = "in-progress"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-10-03T16:30:09Z"
updated = "2026-10-03T19:21:29Z"
scope = ["crates/frob-check/src/scope.rs", "crates/frob-land/src/land.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/src/ledger.rs", "crates/frob-ledger/tests/ledger.rs"]

[[acceptance]]
text = "Given the ledger directory configuration, when frob-check scope and frob-land retry classify a path, then both call the single frob-ledger function"
bound = true
+++

~VMHTBE7 re-implemented the '<ledger dir>/' prefix test in frob-land because branch_changes in frob-check/src/scope.rs is private. Move the classification to frob-ledger (it owns the ledger dir) and call it from both.
