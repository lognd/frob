+++
id = "01M5XD3SGEGXC7MSTTQJRW4R9E"
title = "Rust coverage via cargo-llvm-cov under the nextest provider"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XD3SCZ3VFWNYXJC8FPN9FB"
reporter = "lognd"
created = "2026-10-27T00:45:38Z"
updated = "2026-10-27T02:38:01Z"
scope = ["crates/frob-evidence/src/coverage/rust.rs", "crates/frob-evidence/tests/coverage_rust.rs", "crates/frob-evidence/src/coverage/mod.rs", "docs/design/testing.md"]

[[links]]
kind = "blocked-by"
target = "01M5XD3T31J311PC2KD9Q1N24Q"

[[acceptance]]
text = "Given a test run through the provider with coverage enabled, when it finishes, then a normalised lcov report is written under .git/frob and the coverage figure is recorded on the evidence record"
bound = true

[[acceptance]]
text = "Given a [[coverage.threshold]] scope below its minimum for this language, when frob check runs, then COV004 reports it, and a tool that is missing is reported as not run rather than passing"
bound = false
+++
