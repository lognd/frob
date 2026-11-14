+++
id = "01M7AV38DKR1SA56E17SY378XX"
title = "DEAD001 errors on every unexported Go function (verify with a fixture first)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-14T01:31:05Z"
labels = ["no-story"]
scope = ["crates/grimble-*/**", "crates/gob-symbols/src/go.rs", "crates/gob-symbols/src/graph.rs", "crates/gob-symbols/src/graph/go.rs"]

[[acceptance]]
text = "Go fixture with a called unexported function has no DEAD001."
bound = true
+++

H6: inferred from code: the Go adapter emits no call sites. Confirm with a two-function Go fixture before fixing. Source: frob-audit-grimble-crunk.md (Opus audit).
