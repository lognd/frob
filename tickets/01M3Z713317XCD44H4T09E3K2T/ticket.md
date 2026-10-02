+++
id = "01M3Z713317XCD44H4T09E3K2T"
title = "gob-cli: --schema without positionals and three-word verb paths"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T21:06:23Z"
idempotency_key = "m2-clischema"
labels = ["milestone:2"]
scope = ["crates/gob-cli/**", "crates/gob-macros/**", "crates/frob-evidence/**", "crates/frob/**", "docs/reference/**"]

[[acceptance]]
text = "Given frob work --schema with no ticket, when run, then a schema prints and exit is 0"
bound = false
+++

D40 known limitations: --schema must not require positional arguments; verb paths may have three words so ticket evidence add|list|fetch become real subcommands; CommandMeta and the generated CLI reference follow.
