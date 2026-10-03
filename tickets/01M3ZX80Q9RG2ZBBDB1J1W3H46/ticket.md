+++
id = "01M3ZX80Q9RG2ZBBDB1J1W3H46"
title = "Nested grimble.toml loads only from [workspace] members or explicit root"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:39Z"
updated = "2026-10-03T03:34:39Z"
idempotency_key = "m2-sec-nested-config"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-config/src/workspace.rs"]

[[acceptance]]
text = "Given a grimble.toml under a vendored directory not listed in members, when checking, then it is not loaded"
bound = false

[[acceptance]]
text = "Given the same path listed in members, when checking, then it loads as its own root"
bound = false
+++

Implements security.md section 2.9 (last bullet).

Materialized [workspace] members; vendored, ignored and submodule paths never trigger nested loading.
