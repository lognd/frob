+++
id = "01M7AV38DKR1SA56E17SY378XX"
title = "DEAD001 errors on every unexported Go function (verify with a fixture first)"
type = "bug"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-13T16:15:50Z"
labels = ["no-story"]
scope = ["crates/grimble-*/**"]

[[acceptance]]
text = "Go fixture with a called unexported function has no DEAD001."
bound = false
+++

H6: inferred from code: the Go adapter emits no call sites. Confirm with a two-function Go fixture before fixing. Source: frob-audit-grimble-crunk.md (Opus audit).
