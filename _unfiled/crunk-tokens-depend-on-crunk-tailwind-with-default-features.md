+++
id = "01M4DVX0SRX3HW57XKGEHFB7JE"
title = "crunk-tokens: depend on crunk-tailwind with default-features = false so the token crate does not pull the node runtime stack"
type = "task"
category = "in-progress"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-08T13:40:32Z"
updated = "2026-11-15T04:43:18Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-tokens/Cargo.toml"]

[[acceptance]]
text = "crunk-tokens depends on crunk-tailwind with default-features = false and still builds and passes its tests"
bound = true
+++

Found while working ~1WS0DQ4: crunk-tailwind gained a default-on runtime feature (gob-exec, gob-cache, gob-symbols, ...). crunk-tokens only needs the default-theme tables; set default-features = false there. Blocked by neither; do after ~1WS0DQ4 lands.

no-story: internal engineering task in crunk-tokens; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
