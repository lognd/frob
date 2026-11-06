+++
id = "01M4P0SX8PWMV49CTPDX2SAP57"
title = "dup T0: diff-scoped normalized token-window clone check in frob check (DUP001/DUP002), error by default"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-11-06T04:40:50Z"
scope = ["crates/grimble-arch/src/dup.rs", "crates/grimble-arch/src/lib.rs", "crates/grimble-arch/src/rules/dup001.md", "crates/grimble-arch/src/rules/dup002.md", "crates/grimble-arch/src/rules/dup002.rs", "crates/grimble-arch/src/rules/mod.rs", "crates/grimble-arch/tests/rules.rs", "crates/grimble/src/explain_cmd.rs", "docs/README.md", "docs/design/dup.md", "docs/reference/rules/DUP001.md", "docs/reference/rules/DUP002.md", "docs/reference/rules/README.md", "changelog.d/01M4P0SX8PWMV49CTPDX2SAP57.added.md"]

[[acceptance]]
text = "A diff that adds a clone of an existing symbol fails frob check with DUP001 (exact) or DUP002 (renamed identifiers)"
bound = true

[[acceptance]]
text = "Warm-cache run on an unchanged tree adds under 50 ms; typical diff adds under 1 s (telemetry before/after)"
bound = false

[[acceptance]]
text = "Mutating one input file produces a cache miss"
bound = false

[[acceptance]]
text = "Default severity is error; no opt-in knob required"
bound = false
+++
