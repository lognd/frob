+++
id = "01M4P2N1GFSA69RHJR4D41NVHV"
title = "agent: idempotent install/uninstall that only touches frob-owned hook entries"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:26Z"
updated = "2026-10-28T12:55:50Z"
labels = ["no-story"]
scope = ["crates/frob-cli/**"]

[[acceptance]]
text = "install appends frob hook entries to settings.json, preserving every other key and entry byte-for-byte in meaning"
bound = false

[[acceptance]]
text = "running install twice yields an identical file (idempotent)"
bound = false

[[acceptance]]
text = "each frob entry carries a frob-owned marker; uninstall removes only marked entries, leaving user entries added before or after"
bound = false

[[acceptance]]
text = "install --check and uninstall --dry-run report the planned diff without writing"
bound = false

[[acceptance]]
text = "install never overwrites an existing entry it does not own; conflicts are reported"
bound = false
+++

no-story: internal engineering task in frob-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
