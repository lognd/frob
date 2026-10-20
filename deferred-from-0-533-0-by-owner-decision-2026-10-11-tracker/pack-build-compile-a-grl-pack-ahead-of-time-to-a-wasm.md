+++
id = "01M3ZX7SMJ1W3K92Z6J59CYGQT"
title = "pack build: compile a GRL pack ahead of time to a WASM component"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:32Z"
updated = "2026-10-03T03:34:32Z"
idempotency_key = "m2-wasm-pack-build"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-wasm/src/build/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7HGX4HXKW1X8VKHW9BKW"

[[links]]
kind = "blocked-by"
target = "01M3ZX7SCND92D383E8X9CEWJ7"

[[acceptance]]
text = "Given a tier-2 pack, when `pack build` runs, then a component is produced and a record of toolchain and source tree digest is written"
bound = false

[[acceptance]]
text = "Given the component, when run on the conformance corpus, then findings equal the plan form"
bound = false
+++

Implements plugins.md section 6.1 (last paragraph).

Plugin authors who need built-in-class speed build their pack to a component with tier-2 semantics; the build records toolchain and source tree digest.
