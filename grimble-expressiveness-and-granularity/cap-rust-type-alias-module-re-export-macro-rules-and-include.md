+++
id = "01M64230DV9KGPE0JH2D37NDVN"
title = "CAP: Rust type alias, module re-export, macro_rules and include! forms are not resolved"
type = "task"
category = "in-progress"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-30T07:01:51Z"
idempotency_key = "vnvd3q1-rust-names"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "docs/design/binding.md", "docs/design/output-atoms.md"]

[[acceptance]]
text = "type aliases, pub use chains across modules and files, macro_rules expansion bodies and include! targets resolve to the origin path"
bound = true
+++

Cases r02 r03 r04 r05 r06. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
