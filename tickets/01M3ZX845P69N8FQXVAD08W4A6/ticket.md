+++
id = "01M3ZX845P69N8FQXVAD08W4A6"
title = "frob mirror push [--dry-run] and full resync"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:34:43Z"
idempotency_key = "m2-mirror-push-verb"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/mirror_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX841SP0ZXM4CT18A4B8CV"

[[acceptance]]
text = "Given pending events, when `frob mirror push --dry-run` runs, then the planned operations are printed and nothing is sent"
bound = false

[[acceptance]]
text = "Given `frob mirror push --full-resync`, when run, then every ticket is diffed against the tracker"
bound = false
+++

Implements mirror.md section 3 (who runs it).

One writer; local pushes are opt-in; --dry-run previews the operations.
