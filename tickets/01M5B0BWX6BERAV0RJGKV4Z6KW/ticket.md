+++
id = "01M5B0BWX6BERAV0RJGKV4Z6KW"
title = "Mirror config: add [mirror] bot_ids and feed it to TICK010 instead of an empty list"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:16:33Z"
updated = "2026-10-20T01:01:38Z"
scope = ["crates/frob-check/src/product.rs", "crates/frob-config/**"]

[[acceptance]]
text = "TICK010 renders the expected nudge with numeric [mirror] bot_ids; logins are skipped"
bound = true
+++

Found while working ~Z9B82RZ. tick010_findings renders the expected nudge with empty bot_ids because no [mirror] config exists; an installed nudge with real bot ids is then flagged as edited. Add the config and use it.
