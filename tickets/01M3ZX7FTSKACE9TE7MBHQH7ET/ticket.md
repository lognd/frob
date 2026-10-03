+++
id = "01M3ZX7FTSKACE9TE7MBHQH7ET"
title = "Pack lock: pin tree digest and semantic digests; read, write, verify"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:22Z"
updated = "2026-10-03T03:34:22Z"
idempotency_key = "m2-packs-lock"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/lock/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FPXFVAXEF6QJCFZ0A54"

[[acceptance]]
text = "Given a pack and a lock, when a documentation-only file is edited, then the semantic digests match but the tree digest differs and verify reports exactly that"
bound = false

[[acceptance]]
text = "Given a lock missing an enabled pack, when verified, then a typed lock-missing result is returned for PACK001"
bound = false
+++

Implements packs.md sections 2.5 and 4; security.md section 2.1.

grimble.packs.lock (file name parameterized per product): name, version, tree digest, effects, semantic item digests that stay noise-free input of PACK001 drift reporting; only an explicit update writes it.
