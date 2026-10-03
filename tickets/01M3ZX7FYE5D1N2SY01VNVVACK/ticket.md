+++
id = "01M3ZX7FYE5D1N2SY01VNVVACK"
title = "Std pack: compiled-in plan bytes, registry entry, lock entry frozen to the binary"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:22Z"
updated = "2026-10-03T03:34:22Z"
idempotency_key = "m2-packs-std-skeleton"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/std/**", "packs/std/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FKFSHB8KZM2N4CNF0P9"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FTSKACE9TE7MBHQH7ET"

[[acceptance]]
text = "Given a binary, when `packs list --json` runs, then std appears with source builtin and a digest, and each hand-written tier-0 family is listed as a known exception"
bound = false

[[acceptance]]
text = "Given a plugin pack declaring family CAP, when loaded, then PACK004 is raised because std owns it"
bound = false
+++

Implements plugins.md sections 2, 6.1 and 11.2.

std is a pack like any other: GRL sources under packs/std, plans compiled in via include_bytes!, hand-written tier-0 Rust rules recorded as known exceptions in the std manifest, listed in the lock with a digest frozen to the binary version.
