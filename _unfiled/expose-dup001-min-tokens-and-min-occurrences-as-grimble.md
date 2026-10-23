+++
id = "01M5HMKRFRZYFQC6HVNPHC3Z2P"
title = "Expose DUP001 min_tokens and min_occurrences as grimble-check config knobs"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T11:05:48Z"
updated = "2026-10-23T04:54:27Z"
scope = ["crates/grimble-check/**", "crates/grimble-arch/**", "docs/reference/config.md", "docs/reference/rules/DUP001.md", "docs/schemas/config.json", "docs/guides/grimble.md"]

[[acceptance]]
text = "grimble-check config accepts DUP001 min_tokens and min_occurrences and passes them to the DUP001 pass"
bound = true

[[acceptance]]
text = "omitting the knobs keeps the defaults 50 and 3"
bound = true
+++

found while working ~MAWDT22: DUP001 uses constants MIN_TOKENS=50 and MIN_OCCURRENCES=3 in crates/grimble-arch/src/dup.rs because ArchInput is built literally in grimble-check product.rs; add config fields and pass them through.
