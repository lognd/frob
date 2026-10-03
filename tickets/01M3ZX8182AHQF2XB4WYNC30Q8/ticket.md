+++
id = "01M3ZX8182AHQF2XB4WYNC30Q8"
title = "frob-gh: GitHub HTTPS client with ETags, backoff and recorded fixtures"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:40Z"
updated = "2026-10-03T03:34:40Z"
idempotency_key = "m2-mirror-gh-client"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-gh/**"]

[[acceptance]]
text = "Given a 429 with Retry-After, when a request is made, then the client waits at least that long and retries within the cap"
bound = false

[[acceptance]]
text = "Given recorded fixtures, when the test suite runs offline, then no network is used"
bound = false
+++

Implements mirror.md section 3 (rate limits); git-io.md; boundaries.md (frob-gh).

New crate, tokio only here. Token from the environment, conditional requests, exponential backoff honouring Retry-After, recorded fixtures for offline tests; no gh CLI.
