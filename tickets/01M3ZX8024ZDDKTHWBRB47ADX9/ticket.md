+++
id = "01M3ZX8024ZDDKTHWBRB47ADX9"
title = "Plugin findings name file handles from the subject set, never strings"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:38Z"
updated = "2026-10-03T03:34:38Z"
idempotency_key = "m2-sec-finding-handles"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-packs/src/finding_handle.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7JN8RWAKDVYK0BNG3E2K"

[[links]]
kind = "blocked-by"
target = "01M3ZX7YW7S3BJ72FPRQ85F72V"

[[acceptance]]
text = "Given a plugin finding naming a path string outside its subject set, when accepted, then it is dropped and reported"
bound = false

[[acceptance]]
text = "Given a valid handle with an out-of-range byte range, when accepted, then it is dropped and reported"
bound = false
+++

Implements security.md section 2.10 (handles, not names) (I5).

Byte ranges validated against the file; snippets render only from the in-memory snapshot of tracked, non-ignored files the run already parsed; secondary spans only in files the plugin was given.
