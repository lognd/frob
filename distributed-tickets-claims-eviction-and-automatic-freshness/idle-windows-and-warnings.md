+++
id = "01M5CW04YABDJW6ZXSWFGTCB9E"
title = "Idle windows and warnings"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T19:31:14Z"
idempotency_key = "dt-DT12"
scope = ["crates/frob-ledger/src/claim_window.rs", "crates/frob-ledger/src/lib.rs", "crates/frob/src/config.rs", "docs/reference/config.md"]

[[links]]
kind = "blocked-by"
target = "01M5CW04TYF2SQ101BQB1BGNPJ"
+++

[claims] config: window default 3 calendar days, 4h agents, class and ticket overrides, 0 = never; 50 and 80 percent warnings, aggregated notices. See docs/design/distributed-tickets.md.
