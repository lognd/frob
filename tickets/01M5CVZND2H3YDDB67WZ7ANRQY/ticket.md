+++
id = "01M5CVZND2H3YDDB67WZ7ANRQY"
title = "Distributed tickets: claims, eviction and automatic freshness"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-20T14:38:26Z"
updated = "2026-10-20T14:38:26Z"
idempotency_key = "dt-epic"
+++

Make the ticket ledger safe for many people and agents: publish claims, evict abandoned ones after an adjustable idle window (default 3 calendar days, 4h for agents), and keep the ledger fresh automatically without a remembered command. Design: docs/design/distributed-tickets.md. Related: ~RR15A7Z (claims epic), ~128J4NT, ~RF7ZZHA, ~A2J8C05.
