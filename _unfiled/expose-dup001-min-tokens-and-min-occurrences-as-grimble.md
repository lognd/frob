+++
id = "01M5HMKRFRZYFQC6HVNPHC3Z2P"
title = "Expose DUP001 min_tokens and min_occurrences as grimble-check config knobs"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T11:05:48Z"
updated = "2026-10-22T11:05:48Z"
scope = ["crates/grimble-check/**", "crates/grimble-arch/**"]
+++

found while working ~MAWDT22: DUP001 uses constants MIN_TOKENS=50 and MIN_OCCURRENCES=3 in crates/grimble-arch/src/dup.rs because ArchInput is built literally in grimble-check product.rs; add config fields and pass them through.
