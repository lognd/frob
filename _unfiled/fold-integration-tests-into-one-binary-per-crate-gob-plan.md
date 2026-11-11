+++
id = "01M5AH5JFD9MVN1H1B6YHPX7GN"
title = "Fold integration tests into one binary per crate: gob-plan, frob-ledger, crunk, crunk-rules, crunk-check (tests/*.rs to tests/main.rs)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-19T16:50:57Z"
updated = "2026-11-11T23:40:50Z"
labels = ["no-story"]
scope = ["crates/gob-plan/tests/**", "crates/frob-ledger/tests/**", "crates/crunk/tests/**", "crates/crunk-rules/tests/**", "crates/crunk-check/tests/**"]

[[acceptance]]
text = "Each of gob-plan, frob-ledger, crunk, crunk-rules, crunk-check has its loose tests/*.rs folded into one tests/it/main.rs binary with every test preserved"
bound = true

[[acceptance]]
text = "frob check --ticket ~YHPX7GN passes (COV001 markers intact)"
bound = true
+++

found while working ~ZM1HA1J: cargo dev test-size now measures the total; consolidation of tests/*.rs is outside that ticket's scope. Measure before/after with cargo dev test-size.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
