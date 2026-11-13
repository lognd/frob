+++
id = "01M7AYFA4EZJMYASA6P8EA6SJK"
title = "warnings: tune COH002/COH004/DEAD001 via config so they stop drowning real findings"
type = "chore"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-13T17:14:51Z"
updated = "2026-11-13T17:23:11Z"
labels = ["no-story"]
scope = ["frob.toml", "grimble.toml", "crates/grimble-check/**"]

[[acceptance]]
text = "Unresolved count of COH002+COH004+DEAD001 drops by at least 90 percent without disabling the rules."
bound = false
+++

7054 unresolved findings on CI: COH004 5702, COH002 993, DEAD001 246. Mostly adapter effect_calls/trivial gaps and vocabulary thresholds; tune [coh] effect_calls/trivial and DEAD001 scoping, or fix the adapter. Do not blanket-waive.
