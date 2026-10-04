+++
id = "01M42G1XH9FARCHDA7KCE69AVN"
title = "gob-cache shared test two_processes_open_and_write_one_fresh_cache_without_loss is flaky"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T03:41:51Z"
updated = "2026-10-04T05:22:50Z"
scope = ["crates/gob-cache/**"]

[[acceptance]]
text = "the test passes 50 consecutive runs"
bound = true
+++

found while working ~2GXRW72: fails about 1 in 3 alone (tests/shared.rs:67 and :100, child exits non-success) and once in cargo dev ci
