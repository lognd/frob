+++
id = "01M4GRW6NH23YPTSAQERDRSZC5"
title = "Scoped tool stages at land: cargo clippy/fmt over affected crates and reverse deps; dev gen --check only when its inputs changed"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4GRTA9XBJCM2RY98HWZXYC7"
reporter = "lognd"
created = "2026-10-09T16:45:23Z"
updated = "2026-10-09T21:23:26Z"
scope = ["changelog.d/**", "frob.toml", "crates/gob-check/src/config.rs", "crates/gob-check/src/tools.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/Cargo.toml", "Cargo.lock", "crates/gob-check/src/tool_parse.rs", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given the fast-lands epic design, when this lands, then the behaviour in the title holds with a test"
bound = true

[[acceptance]]
text = "Given a tool stage whose declared inputs (paths) the ticket does not touch, when the ticket lands, then that stage is not run or gated at land (it runs on CI); stages declare inputs in frob.toml (logand F-569/F-570)"
bound = true
+++
