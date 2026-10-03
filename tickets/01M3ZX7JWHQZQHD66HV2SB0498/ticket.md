+++
id = "01M3ZX7JWHQZQHD66HV2SB0498"
title = "Path-scoped activation: [[packs.enable]] with paths and required"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:25Z"
updated = "2026-10-03T03:34:25Z"
idempotency_key = "m2-packs-activation"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/activation.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[acceptance]]
text = 'Given `[[packs.enable]] name="react" paths=["frontend/**"]`, when resolving frontend/a.tsx and backend/b.ts, then react is active only for the first and the answer names the config line'
bound = false

[[acceptance]]
text = "Given a pack.toml in a subdirectory, when resolving files beneath it, then nothing changes"
bound = false
+++

Implements plugins.md section 2 (no directory-scoped packs).

One root config says what applies where. A nested pack.toml or grimble.toml does not change what applies below it; a nested grimble.toml is a separate project.
