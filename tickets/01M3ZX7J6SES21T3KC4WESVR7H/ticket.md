+++
id = "01M3ZX7J6SES21T3KC4WESVR7H"
title = "gob-trust crate: per-machine key and MAC primitives"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T06:18:19Z"
idempotency_key = "m2-sec-trust-core"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/**"]

[[acceptance]]
text = "Given a value MAC'd with the machine key, when verified, then it passes, and when one byte is changed it fails"
bound = true

[[acceptance]]
text = "Given no key file, when first used, then a key is created with owner-only permissions and a group- or world-writable key is reported by a typed error"
bound = true
+++

Implements security.md sections 2.2 and 2.3.

Shared crate for frob, grimble and crunk. Per-machine key stored beside the trust store (XDG config), HMAC over entries, constant-time verify; hand-added entries are inert.
