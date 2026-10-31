+++
id = "01M6997C8YTYQ65AWZSW05P4HZ"
title = "CI red: crunk cache profile scenarios and crunk crates depending on frob-present"
type = "bug"
category = "todo"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T15:28:35Z"
updated = "2026-10-31T15:28:35Z"
idempotency_key = "ci-green-crunk-profile-boundary"
scope = ["crates/gob-dev/profile.toml", "crates/crunk*/**", "crates/gob-term/**", "changelog.d/**"]

[[acceptance]]
text = "profile.toml has a scenario or skip reason for crunk cache ls and crunk cache prune so the command-budgets job passes"
bound = false

[[acceptance]]
text = "No crunk crate depends directly or transitively on a frob crate, so crunk::boundary passes"
bound = false
+++

CI run 41211322397: profile failed (leaf commands crunk cache ls, crunk cache prune have no scenario or skip) and crates/crunk/tests/boundary.rs:59 reports crunk crates depend on frob crates: [frob-present] (likely introduced by the gob-term/DWMMH0A layering; frob-present should not be reachable from crunk).
