+++
id = "01M3ZKK62R05XCKFDVCFRHX0KM"
title = "Adopt grimble in this repository: grimble.toml, exclude test corpora, ignore .grimble/, fix the compute digest example"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T00:45:59Z"
updated = "2026-10-03T01:16:03Z"
idempotency_key = "m2-grimble-adopt"
labels = ["milestone:2"]
scope = ["grimble.toml", "frob.toml", ".gitignore", "design/**", "docs/design/sibling-contract.md"]

[[acceptance]]
text = "Given this repository, when grimble check --json runs, then no finding comes from a test corpus file and the document validates"
bound = false
+++

From ~EHPFVKD: grimble check on this repository walks the deliberately broken .grmb corpora under crates/*/tests/corpus and reports their MDL, PARSE and DSL findings as noise; run grimble init here, exclude test corpora (crates/*/tests/corpus/** and crates/*/tests/mdtest*/**) in grimble.toml and frob.toml [check] exclude where frob also walks them, add .grimble/ to .gitignore, and correct the compute_digest in docs/design/sibling-contract.md section 9 (the blake3 of the canonical default object is d2159af7..., not bfc07185...; recompute and state how).
