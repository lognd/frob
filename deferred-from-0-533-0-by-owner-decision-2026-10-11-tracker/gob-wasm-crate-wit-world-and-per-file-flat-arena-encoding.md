+++
id = "01M3ZX7S1ZBWEC0PE895ZC6KXN"
title = "gob-wasm crate: WIT world and per-file flat arena encoding"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:31Z"
updated = "2026-10-03T03:34:31Z"
idempotency_key = "m2-wasm-wit"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-wasm/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JN8RWAKDVYK0BNG3E2K"

[[acceptance]]
text = "Given a file, when the arena is built, then it round-trips to the same U term and scope graph"
bound = false

[[acceptance]]
text = "Given the WIT world, when a component is checked against it, then a missing hook is rejected with PACK005"
bound = false
+++

Implements plugins.md sections 3 and 6.3.

Feature-gated crate. One flat arena per file (U term, scope graph, attributes, location table) so the guest is called once per file, never per node.
