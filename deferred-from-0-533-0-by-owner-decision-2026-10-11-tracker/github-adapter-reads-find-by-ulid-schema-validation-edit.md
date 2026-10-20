+++
id = "01M3ZX83NZ4PAM53VQCHXPE1R8"
title = "GitHub adapter reads: find-by-ULID, schema validation, edit history"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T05:51:57Z"
idempotency_key = "m2-mirror-gh-read"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-gh/src/read.rs", "crates/frob-mirror/src/github/read.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[acceptance]]
text = "Given a mapping naming a missing label, when the run starts, then it fails with one diagnostic and a remedy before any write"
bound = false

[[acceptance]]
text = "Given an issue already carrying the ULID marker, when first synced, then it is adopted and not duplicated"
bound = false
+++

Implements mirror.md section 3 (identity, schema drift).

Find an issue by its hidden ULID marker, validate the mapping against the project's labels, fields and states before any write, read edit history (user and time) where the API has it.
