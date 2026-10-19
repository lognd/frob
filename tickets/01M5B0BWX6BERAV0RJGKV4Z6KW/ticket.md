+++
id = "01M5B0BWX6BERAV0RJGKV4Z6KW"
title = "Mirror config: add [mirror] bot_ids and feed it to TICK010 instead of an empty list"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T21:16:33Z"
updated = "2026-10-19T21:16:33Z"
scope = ["crates/frob-check/src/product.rs", "crates/frob-config/**"]
+++

Found while working ~Z9B82RZ. tick010_findings renders the expected nudge with empty bot_ids because no [mirror] config exists; an installed nudge with real bot ids is then flagged as edited. Add the config and use it.
