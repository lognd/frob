+++
id = "01M4H4WTSTB7X4A6STFEF8K8S3"
title = "PacksTable doc comment still says 'Packs are not loaded yet' after ~AMVHK82 loads local packs; fix it and regenerate config.json and config.md"
type = "docs"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T20:15:26Z"
updated = "2026-10-09T20:15:26Z"
labels = ["grimble"]
scope = ["crates/grimble-check/src/config.rs", "docs/schemas/config.json", "docs/reference/config.md", "changelog.d/**"]

[[acceptance]]
text = "Given ~AMVHK82 landed, when the docs regenerate, then the PacksTable doc and both generated references describe what loads (local/ packs, atoms only) and what does not yet"
bound = false
+++

Reported by ~AMVHK82's implementer.
