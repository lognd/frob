+++
id = "01M47QVC49RXV29NCG3N9G1JSM"
title = "Deterministic instruction-count PR benchmarks compared against the base"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:12Z"
updated = "2026-10-06T04:34:12Z"
scope = ["crates/*/benches/**", "crates/gob-dev/**", ".github/workflows/**", "docs/design/build-test-ci.md", "Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "benchmarks run under the harness on Linux"
bound = false

[[acceptance]]
text = "the PR comment lists per-benchmark instruction deltas"
bound = false

[[acceptance]]
text = "the harness choice is recorded in build-test-ci.md"
bound = false
+++

build-test-ci.md section 6, ruff on CodSpeed but with no external service. Pin a maintained Valgrind-based instruction-count harness (iai-callgrind or its successor; record the choice) for cold and warm check, the plan executor and the parsers; a PR job runs base and head on Linux and comments the deltas; criterion stays for scheduled wall-clock runs.
