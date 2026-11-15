+++
id = "01M7GPH1Y4XQ9RZMAV1HQG7JPX"
title = "Wire [path] allowed config into PATH001 Options::with_allowed callers"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T22:51:26Z"
updated = "2026-11-15T22:51:26Z"
idempotency_key = "path-allowed-wiring"
scope = ["crates/grimble-lints/src/path.rs"]

[[acceptance]]
text = "A configured [path] allowed list reaches PATH001 through Options::with_allowed in every caller, covered by a test"
bound = false
+++

Follow-up of AHK30R3: Options::with_allowed exists but no caller outside grimble-lints reads the [path] allowed config.
