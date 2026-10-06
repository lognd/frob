+++
id = "01M3ZX8182AHQF2XB4WYNC30Q8"
title = "frob-gh: GitHub HTTPS client with ETags, backoff and recorded fixtures"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:40Z"
updated = "2026-10-06T07:33:18Z"
idempotency_key = "m2-mirror-gh-client"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-gh/**", "Cargo.lock"]

[[acceptance]]
text = "Given a 429 with Retry-After, when a request is made, then the client waits at least that long and retries within the cap"
bound = true

[[acceptance]]
text = "Given recorded fixtures, when the test suite runs offline, then no network is used"
bound = true
+++

Implements mirror.md section 3.2 (transport and rate-limit headers); git-io.md; boundaries.md (frob-gh).

New crate, tokio only here. Token from the environment, REST and GraphQL calls, conditional requests (ETags), the rate-limit headers (remaining, used, reset) exposed to the caller as typed values or as an explicit absence, backoff honouring Retry-After, recorded fixtures for offline tests; no gh CLI. The stop-instead-of-sleep rule, the 60 s doubling, and GraphQL errors arrays are the error-policy ticket (m2-mirror2-gh-error-policy), which builds on this client.
