+++
id = "01M4W7KGANMJNZYEBTTNW7Q9WN"
title = "Rust test provider: configurable crate exclusion ([tests] rust_exclude) instead of hardcoded --workspace"
type = "story"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T03:34:25Z"
updated = "2026-10-27T02:58:19Z"
idempotency_key = "tests-rust-exclude-20261013"
scope = ["crates/frob/**"]

[[acceptance]]
text = "Given rust_exclude lists a workspace crate, when frob test --all runs, then the crate is excluded from the cargo/nextest invocation and the knob appears in the config reference and schema."
bound = false
+++

Adopter request (cadetta, their ticket ~7PF9F6T): frob test --all runs `cargo nextest run --workspace` and builds a pyo3 crate that cannot link under the adopter interpreter; their own gates use --exclude. Add a materialized config knob (for example [tests] rust_exclude = ["crate"]) that the Rust test provider turns into --exclude flags, include it in the config reference/schema and the PyPI-published schema, and document it. A nextest default-filter is not enough because nextest still builds every package.
