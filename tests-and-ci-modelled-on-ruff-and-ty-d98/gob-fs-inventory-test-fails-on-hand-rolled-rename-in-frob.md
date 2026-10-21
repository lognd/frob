+++
id = "01M5FNMF22M7XZN56NPY6S4ERK"
title = "gob-fs inventory test fails on hand-rolled rename in frob-ledger/src/refresh.rs"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T16:45:11Z"
updated = "2026-10-21T16:54:48Z"
scope = ["crates/frob-ledger/src/refresh.rs", "crates/frob-ledger/Cargo.toml", "Cargo.lock", "changelog.d/01M5FNMF22M7XZN56NPY6S4ERK.fix.md"]

[[acceptance]]
text = "Refresh state save goes through gob_fs::write_atomic with no hand-rolled rename, so the gob-fs inventory test passes"
bound = true

[[acceptance]]
text = "Refresh state still round-trips through save and load unchanged"
bound = false
+++

Found while landing KHR84D9; failing test on experimental. Fix or waive with reason.
