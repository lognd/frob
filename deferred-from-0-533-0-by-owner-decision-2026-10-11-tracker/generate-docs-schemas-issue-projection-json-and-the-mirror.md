+++
id = "01M3ZX836BNV9H9K9ZCKNMAEDB"
title = "Generate docs/schemas/issue-projection.json and the mirror render verb"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-19T18:19:20Z"
idempotency_key = "m2-mirror-schema-gen"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/gob-dev/src/render/**", "docs/schemas/issue-projection.json", "crates/frob/src/mirror_cmd.rs", "crates/frob-mirror/src/projection.rs", "crates/frob-mirror/Cargo.toml", "crates/gob-dev/Cargo.toml", "crates/frob/Cargo.toml", "crates/frob/src/lib.rs", "crates/frob/src/product.rs", "Cargo.lock", "crates/frob/tests/it/mirror_render.rs", "docs/design/mirror.md", "docs/reference/cli/frob.md", "crates/frob/tests/it/main.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX832JK52FXBPPCCGTDRTG"

[[acceptance]]
text = "Given the Rust type, when `cargo dev gen all --check` runs, then docs/schemas/issue-projection.json is current"
bound = true

[[acceptance]]
text = "Given `frob mirror render ~X --json`, when run, then the output validates against that schema"
bound = true
+++

Implements mirror.md section 2.1 (last paragraph).

`cargo dev gen schemas` writes the schema from the Rust type; `frob mirror render <ticket>` prints a projection so other adapters develop from recorded projections.
