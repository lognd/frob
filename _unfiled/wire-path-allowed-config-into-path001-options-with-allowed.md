+++
id = "01M7GPH1Y4XQ9RZMAV1HQG7JPX"
title = "Wire [path] allowed config into PATH001 Options::with_allowed callers"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T22:51:26Z"
updated = "2026-11-16T01:49:15Z"
idempotency_key = "path-allowed-wiring"
labels = ["no-story"]
scope = ["crates/grimble-lints/src/path.rs", "crates/grimble-check/src/config.rs", "crates/grimble-check/src/product.rs", "docs/reference/config/frob.md"]

[[acceptance]]
text = "A configured [path] allowed list reaches PATH001 through Options::with_allowed in every caller, covered by a test"
bound = false
+++

no-story: small follow-up wiring an existing config key; no user story applies.
