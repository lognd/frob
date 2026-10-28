+++
id = "01M5D9NM3SST8N2HGFV7Y3WV9P"
title = "Add [sync] warn_after_secs/stale_error_secs and feed Thresholds"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T18:37:37Z"
updated = "2026-10-28T12:55:45Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/src/config.rs", "docs/schemas/config.json", "docs/reference/config.md", "crates/frob/src/refresh_cmd.rs"]
+++

found while working ~8PE22M6: freshness Thresholds use defaults (1h/24h); add the config keys and pass them in.

no-story: internal engineering task in frob-ledger; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
