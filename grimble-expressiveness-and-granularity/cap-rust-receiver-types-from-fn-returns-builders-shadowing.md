+++
id = "01M64230GWHHTH9R7CZ55XRPGG"
title = "CAP: Rust receiver types from fn returns, builders, shadowing and generics are not resolved"
type = "task"
category = "todo"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-29T14:47:39Z"
idempotency_key = "vnvd3q1-rust-recv"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**"]

[[acceptance]]
text = "types flow through fn return types and builder chains, inner-scope shadowing does not hide the outer binding, and generic or trait-bound receivers report Unresolved"
bound = false
+++

Cases q01 q03 q04 and r10 (File::options, symlink). symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
