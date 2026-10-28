+++
id = "01M625YHR9M9VW5BK43536T3XN"
title = "org C3: move gob-dev product edges into frob-docgen; gate frob-check -> grimble-check behind bundle"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:39Z"
updated = "2026-10-28T21:16:39Z"
idempotency_key = "org-C3"
scope = ["crates/gob-dev/**"]

[[acceptance]]
text = "gob-dev has no product-crate edges; 5 ALLOWED layering rows removed; ci_parity passes"
bound = false
+++

Breaks cargo dev subcommands and CI argv. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
