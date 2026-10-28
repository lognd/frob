+++
id = "01M625YJ4JQWZS3PNKJ4SF87Q9"
title = "org T2: unify test helper and data dir names; shrink exclude lists"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:39Z"
updated = "2026-10-28T21:16:39Z"
idempotency_key = "org-T2"
scope = ["crates/**/tests/**"]

[[acceptance]]
text = "helpers named support, data dirs fixtures/mdtest; exclude lists in frob.toml and grimble.toml shrink after the data moves"
bound = false
+++

Move data before changing excludes. Follows T1. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
