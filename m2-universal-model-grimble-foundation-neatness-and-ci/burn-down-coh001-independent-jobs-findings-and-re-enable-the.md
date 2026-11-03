+++
id = "01M6G5MV1MCD1MVVETTK4ATJ8E"
title = "Burn down COH001 independent-jobs findings and re-enable the rule"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-11-03T07:40:42Z"
updated = "2026-11-03T16:24:33Z"
labels = ["no-story"]
scope = ["crates/**", "frob.toml", "scripts/claude-hooks/_shellscan.py", "tests/crunk-parity/regen.py"]

[[acceptance]]
text = "Every COH001 finding is extracted into its own unit or carries a baseline entry with a reason"
bound = true

[[acceptance]]
text = "The [rules.COH001] severity=off table is deleted from frob.toml and frob check reports zero COH001"
bound = true
+++

COH001 became default-on (2093914923) and reports 439 errors plus 144 unresolved in CI run 41593367926. Turned off in frob.toml by ~A24NX1C until burned down. Top crates: gob-symbols 43, gob-plan 28, grimble-check 25, gob-check 19, crunk-rules 17, grimble-bind 17, frob-check 16, frob 16.
