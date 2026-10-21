+++
id = "01M5FNMENEHRENY71N3FWFY8TS"
title = "grimble-model allow-list marker in gob-path confinement test allow_list_matches_markers fails"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T16:45:11Z"
updated = "2026-10-21T16:52:53Z"
scope = ["crates/grimble-model/tests/inline.rs", "changelog.d/01M5FNMENEHRENY71N3FWFY8TS.fix.md", "changelog.d/01M5FNMENEHRENY71N3FWFY8TS.fixed.md"]

[[acceptance]]
text = "The gob-path allow_list_matches_markers test passes: grimble-model no longer carries the confinement marker and ALLOW is unchanged"
bound = true
+++

Found while landing KHR84D9; failing test on experimental. Fix or waive with reason.
