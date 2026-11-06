+++
id = "01M6S4ZMB1Y6CCH144TVNC5A27"
title = "Expose grant cells on grimble_bind::Binding for the matrix verb"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-06T19:22:17Z"
updated = "2026-11-06T19:24:52Z"
scope = ["crates/grimble-bind/src/lib.rs", "crates/grimble-bind/src/caps.rs", "crates/grimble-check/src/lib.rs", "crates/grimble-check/src/product.rs", "crates/grimble-check/src/bind_cache.rs", "crates/grimble-bind/src/eval.rs", "crates/grimble-bind/tests/binding_cells.rs"]
+++

Found while working ~4M81218: grant_cells needs a private Cx built inside bind(); Binding/GrimbleRun expose no cells. Also grant_cells yields only grant cells (uses, declared-unused, unknown), not CAP001 undeclared, so the verb needs those separately.
