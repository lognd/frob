+++
id = "01M3ZX7FG2JNTHKVQ5R535DAVZ"
title = "gob-packs crate: pack.toml manifest model and validation"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-04T04:28:10Z"
idempotency_key = "m2-packs-manifest"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/**"]

[[acceptance]]
text = "Given the example manifest of plugins.md section 2, when loaded, then a typed Manifest results with name, version, families, needs, provides and an empty effects table"
bound = true

[[acceptance]]
text = "Given two packs declaring family PYS, or an unknown manifest key, when loaded, then PACK004 and PACK005 are returned as Err values with the file and key named"
bound = false
+++

Implements plugins.md sections 2 and 10.

Product-neutral crate (frob, grimble and crunk use it). Manifest sections pack, provides, effects; families owned by a pack; duplicate family is PACK004; malformed manifest is PACK005 with a located reason.
