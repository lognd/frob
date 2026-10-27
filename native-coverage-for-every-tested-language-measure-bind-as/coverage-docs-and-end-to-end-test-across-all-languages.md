+++
id = "01M5XD3T77PEHA0QDBXC7TFFN3"
title = "Coverage docs and end-to-end test across all languages"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5XD3SCZ3VFWNYXJC8FPN9FB"
reporter = "lognd"
created = "2026-10-27T00:45:39Z"
updated = "2026-10-27T00:45:39Z"
scope = ["docs/guides/coverage.md", "crates/frob/tests/it/coverage_e2e.rs"]

[[acceptance]]
text = "Given a fixture repo with Rust, Python, JS and C# tests, when frob test --coverage then frob check run, then COV004 reports each language against its threshold"
bound = false
+++
