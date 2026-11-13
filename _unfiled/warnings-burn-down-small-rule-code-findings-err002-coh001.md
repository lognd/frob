+++
id = "01M7AYFA9AE50AM4617VSX6B8Q"
title = "warnings: burn down small-rule code findings (ERR002 COH001 LOG001 VIS001 REL003 RES001 FMT001 CYCLE001)"
type = "chore"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-13T17:14:51Z"
updated = "2026-11-13T19:10:34Z"
labels = ["no-story"]
scope = ["crates/**", "grimble.toml"]

[[acceptance]]
text = "Zero unresolved findings for ERR002, COH001, LOG001, VIS001, REL003, RES001, FMT001 in frob check."
bound = false
+++

From the CI frob check: ERR002 3, COH001 18, LOG001 30, VIS001 8, REL003 3, RES001 1, FMT001 1, CYCLE001 1. Fix in code; list each with frob check --text first.
