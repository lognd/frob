+++
id = "01M7EXW4JTYXSZBPGBBZ4ECHME"
title = "grimble-arch: DEAD001 skips or marks Unresolved for languages without call sites (Go)"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:20Z"
updated = "2026-11-15T06:21:20Z"
labels = ["no-story"]

[[acceptance]]
text = "A Go fixture with an unexported helper() called from main raises no DEAD001 Error"
bound = false

[[acceptance]]
text = "Unresolved EdgeUnknown is reported instead"
bound = false
+++

Audit: ~/projects/frob-audit-grimble-crunk.md H6. DEAD001 errors on every unexported Go function; Go adapter crates/gob-symbols/src/go.rs:1-12,81-103 emits no call sites. Files: crates/grimble-arch/src/dead.rs:83-110,150-215, lib.rs:153-155. Remedy: skip or Unresolved (EdgeUnknown) for languages without apply_targets; add Go fixture (main.go with helper(); verify before fixing).
