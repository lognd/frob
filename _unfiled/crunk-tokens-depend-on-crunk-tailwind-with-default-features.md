+++
id = "01M4DVX0SRX3HW57XKGEHFB7JE"
title = "crunk-tokens: depend on crunk-tailwind with default-features = false so the token crate does not pull the node runtime stack"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-08T13:40:32Z"
updated = "2026-10-08T13:40:32Z"
labels = ["area:crunk"]
scope = ["crates/crunk-tokens/Cargo.toml"]
+++

Found while working ~1WS0DQ4: crunk-tailwind gained a default-on runtime feature (gob-exec, gob-cache, gob-symbols, ...). crunk-tokens only needs the default-theme tables; set default-features = false there. Blocked by neither; do after ~1WS0DQ4 lands.
