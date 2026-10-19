+++
id = "01M5AH5JFD9MVN1H1B6YHPX7GN"
title = "Fold integration tests into one binary per crate: gob-plan, frob-ledger, crunk, crunk-rules, crunk-check (tests/*.rs to tests/main.rs)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T16:50:57Z"
updated = "2026-10-19T16:50:57Z"
scope = ["crates/gob-plan/tests/**", "crates/frob-ledger/tests/**", "crates/crunk/tests/**", "crates/crunk-rules/tests/**", "crates/crunk-check/tests/**"]
+++

found while working ~ZM1HA1J: cargo dev test-size now measures the total; consolidation of tests/*.rs is outside that ticket's scope. Measure before/after with cargo dev test-size.
