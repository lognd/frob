+++
id = "01M4CXSH25SNDV9NGGJ1DF39BA"
title = "Exit: hullbreach platform CI runs the Rust crunk instead of uv run crunk, with a reasoned divergence list"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T04:54:20Z"
updated = "2026-10-08T04:54:20Z"
scope = ["changelog.d/**", "crates/crunk/**", "docs/crunk/**"]

[[acceptance]]
text = "Given hullbreach platform, when its CI crunk step runs the Rust crunk, then it passes and every divergence from the Python crunk is listed with a reason"
bound = false
+++

docs/design/crunk.md section 9 phase 1 exit.
