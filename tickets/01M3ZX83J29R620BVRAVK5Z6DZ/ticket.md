+++
id = "01M3ZX83J29R620BVRAVK5Z6DZ"
title = "Mirror map shards on the ticket branch: per-ticket cache of tracker identity, cursors and observed values"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T05:49:56Z"
idempotency_key = "m2-mirror-map-file"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/mapfile.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82Q2N145P3DWVVY4E868"

[[acceptance]]
text = "Given a published ticket, when the map is read back, then ULID, tracker key, last event and hash round-trip"
bound = false

[[acceptance]]
text = "Given a lost map file, when the mirror re-finds issues by ULID marker, then no duplicate is created"
bound = false
+++

Implements mirror.md sections 3.2 (progress), 3.3 (the tracker is the identity authority, the map is a cache) and 3.4 (cursor).

The map is sharded per ticket and committed through CAS on the shard content. A shard holds: ULID, tracker issue number and node id, cached location, last observed value per repository-owned field (normalized), history cursor (tracker event id), create-uncertain flag with nonce and create-start time, round-robin and change-feed cursors live in one small index shard. A lost shard or map is rebuilt from the tracker listing, never by creating. Committed every K operations.
