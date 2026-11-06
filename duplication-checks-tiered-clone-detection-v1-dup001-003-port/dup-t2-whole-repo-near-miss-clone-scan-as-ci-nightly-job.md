+++
id = "01M4P0SXJRVQ0ADAAH3FMYPAR6"
title = "dup T2: whole-repo near-miss clone scan as CI/nightly job with baseline ratchet"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-11-06T07:21:46Z"
labels = ["no-story"]
scope = [".github/workflows/dup-scan.yml", "crates/gob-dev/tests/dup_scan_workflow.rs", "crates/grimble-arch/**", "crates/grimble-check/**", "crates/grimble/src/explain_cmd.rs", "docs/**", "frob-baseline.toml", "frob.lock"]

[[acceptance]]
text = "CI job runs off the critical path and never blocks land"
bound = true

[[acceptance]]
text = "Baseline file records existing clusters; only new clusters fail"
bound = true

[[acceptance]]
text = "Runtime budget documented and measured on this repository"
bound = true
+++

Whole-repo near-miss clone scan (DUP005) as a nightly CI job with a baseline ratchet. no-story: second slice of the dup epic, no story of its own.
