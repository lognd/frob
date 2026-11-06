+++
id = "01M6SD9NZJ8XPWYNGTB233F9ZV"
title = "Grimble LOG rules: Zig and CUDA output atoms (needs gob_languages variants)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-06T21:47:35Z"
updated = "2026-11-06T23:58:17Z"
scope = ["crates/gob-languages/**", "crates/grimble-check/src/log/**", "Cargo.lock", "docs/design/grimble/output-atoms.md"]
+++

found while working ~6NKDAMD: gob_languages::Language has no Zig or CUDA variant, so the planned Zig and CUDA output atoms cannot be scanned yet. Add the grammars/variants, then a LOG scanner for each.
