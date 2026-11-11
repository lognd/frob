+++
id = "01M6SD9NZJ8XPWYNGTB233F9ZV"
title = "Grimble LOG rules: Zig and CUDA output atoms (needs gob_languages variants)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-06T21:47:35Z"
updated = "2026-11-11T00:47:22Z"
scope = ["crates/gob-languages/**", "crates/grimble-check/src/log/**", "Cargo.lock", "docs/design/grimble/output-atoms.md", "crates/gob-symbols/src/lang.rs", "grimble-vet.toml"]

[[acceptance]]
text = "Zig and CUDA sources are scanned for LOG001 output atoms (Zig scanner, CUDA via the C scanner) with fixtures"
bound = true
+++

found while working ~6NKDAMD: gob_languages::Language has no Zig or CUDA variant, so the planned Zig and CUDA output atoms cannot be scanned yet. Add the grammars/variants, then a LOG scanner for each.
