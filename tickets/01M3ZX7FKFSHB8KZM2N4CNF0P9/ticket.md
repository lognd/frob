+++
id = "01M3ZX7FKFSHB8KZM2N4CNF0P9"
title = "Registry merges inventory and loaded packs with provenance per rule"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:22Z"
updated = "2026-10-03T03:34:22Z"
idempotency_key = "m2-packs-registry-provenance"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-rules/src/registry.rs", "crates/gob-rules/src/meta.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[acceptance]]
text = "Given a std rule and a plugin rule, when `rules list --json` runs, then both rows have the same fields and differ only in pack provenance"
bound = false

[[acceptance]]
text = "Given `[rules]` severity and disable settings, when applied, then a std rule and a plugin rule obey them identically"
bound = false
+++

Implements plugins.md sections 6.1 and 10.

One Registry view; built-in and plugin rules both carry provenance (std or the pack name) and appear identically in rules list; a built-in can be disabled exactly like a plugin.
