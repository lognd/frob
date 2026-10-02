+++
id = "01M3Z714XYJEHXHNWXKVXAYFQJ"
title = "G19: grimble-serve MCP"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-02T21:06:25Z"
idempotency_key = "m2-serve"
labels = ["milestone:2"]
scope = ["crates/grimble-serve/**", "crates/gob-serve/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[acceptance]]
text = "Given grimble serve --mcp, when a client lists tools, then check and graph are offered and a request without the token is refused"
bound = false
+++

gob-serve plus grimble: serve --mcp exposing check, graph and explore read-only; per-launch token per D29.
