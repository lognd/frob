+++
id = "01M5XD3T31J311PC2KD9Q1N24Q"
title = "Coverage plumbing: shared lcov normaliser, evidence field, --coverage flag, [coverage] materialised and enforced"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XD3SCZ3VFWNYXJC8FPN9FB"
reporter = "lognd"
created = "2026-10-27T00:45:39Z"
updated = "2026-10-27T00:50:09Z"
scope = ["crates/frob-evidence/src/coverage/mod.rs", "crates/frob-evidence/src/provider.rs", "crates/frob-obligations/src/coverage.rs", "crates/frob-evidence/src/coverage/**", "crates/frob-evidence/src/config.rs", "crates/frob-evidence/src/lib.rs", "crates/frob-evidence/src/record.rs", "crates/frob-evidence/src/verbs.rs", "crates/frob-evidence/src/workspace.rs"]

[[acceptance]]
text = "Given any provider run with --coverage, when it finishes, then the shared normaliser merges per-language reports into one lcov file COV004 reads"
bound = false

[[acceptance]]
text = "Given the [coverage] table, when frob check runs, then it is enforced (Materialized: yes) and a missing report for a language with tests is a finding"
bound = false
+++
