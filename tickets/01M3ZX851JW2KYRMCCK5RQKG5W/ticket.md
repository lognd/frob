+++
id = "01M3ZX851JW2KYRMCCK5RQKG5W"
title = "Authenticated issue markers and MIR003 spoofed-marker"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T03:34:44Z"
idempotency_key = "m2-mirror-markers"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/marker.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[links]]
kind = "blocked-by"
target = "01M3ZX83NZ4PAM53VQCHXPE1R8"

[[acceptance]]
text = "Given an issue created by another user carrying a valid-looking marker, when the mirror runs, then it is ignored and MIR003 is reported"
bound = false

[[acceptance]]
text = "Given a bot issue whose marker HMAC is wrong, when the mirror runs, then it is not adopted"
bound = false
+++

Implements security.md section 2.11; mirror.md section 3.1.

The mirror adopts or updates an issue only if its author is the mirror's bot identity (by user id) and the marker carries an HMAC of the ULID under a CI-secret key; anything else carrying a marker is MIR003 (Advisory) and ignored.
