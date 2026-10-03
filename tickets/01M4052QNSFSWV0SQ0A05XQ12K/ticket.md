+++
id = "01M4052QNSFSWV0SQ0A05XQ12K"
title = "frob-gh: error policy: Retry-After, stop at no budget, 60 s doubling, GraphQL errors arrays"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:35Z"
updated = "2026-10-03T05:51:35Z"
idempotency_key = "m2-mirror2-gh-error-policy"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-gh/src/policy.rs", "crates/frob-gh/src/graphql.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[acceptance]]
text = "Given a 200 GraphQL response whose errors array reports rate limiting, when parsed, then it is a rate-limit failure carrying the reset time and no data is returned"
bound = false

[[acceptance]]
text = "Given partial data with a non-empty errors array, when parsed, then the whole query scope is failed"
bound = false

[[acceptance]]
text = "Given a rate-limited response with no remaining budget, when handled, then the client stops without sleeping and reports the reset time"
bound = false

[[acceptance]]
text = "Given repeated 5xx with budget left and a fake clock, when retried, then waits are 60 s then doubling and the client stops after three retries"
bound = false
+++

Implements mirror.md section 3.2 (Errors).

retry-after is honoured; with no remaining budget the run stops without sleeping to the reset and records the reset time; otherwise wait 60 s, doubling, at most three retries, then stop. Every GraphQL response's errors array is checked (rate limiting arrives there with HTTP 200) and partial data fails that query's scope.
