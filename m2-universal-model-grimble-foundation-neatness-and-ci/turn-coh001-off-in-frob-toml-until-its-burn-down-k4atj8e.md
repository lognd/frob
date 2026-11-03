+++
id = "01M6G5FRN45YZD6MXSGA24NX1C"
title = "Turn COH001 off in frob.toml until its burn-down (~K4ATJ8E)"
type = "chore"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-11-03T07:37:56Z"
updated = "2026-11-03T07:40:51Z"
labels = ["no-story"]
scope = ["frob.toml"]

[[acceptance]]
text = "frob check reports zero COH001 findings with the rule off"
bound = true
+++

COH001 became default-on (registered in 2093914923) and reports 439 errors plus 144 unresolved in CI (run 41593367926), turning experimental red. Set off in frob.toml until burned down. Top crates: gob-symbols 43, gob-plan 28, grimble-check 25, gob-check 19, crunk-rules 17, grimble-bind 17, frob-check 16, frob 16.
