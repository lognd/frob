+++
id = "01M3ZX7T4XJMT10VCQYQRBTYGC"
title = "The .grmb, Rust and markdown adapters become std adapter packs"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:32Z"
updated = "2026-10-03T03:34:32Z"
idempotency_key = "m2-packs-std-adapters"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/std/adapters.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZEH464EFCFAZ4XDKE89D5Z"

[[links]]
kind = "blocked-by"
target = "01M3ZX7T0WTQ93A8DWG8HJZ9MP"

[[acceptance]]
text = "Given the three adapters registered as std packs, when the language conformance suite runs, then results are unchanged"
bound = false

[[acceptance]]
text = "Given `packs list`, when run, then the adapters appear with provenance builtin"
bound = false
+++

Implements plugins.md section 8 (last sentence).

Registration through the same pack API; behaviour must not change.
