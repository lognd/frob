+++
id = "01M6D124NJ6QRDAX1QD2V4GRJE"
title = "grimble-model: marker REF resolution for D157 file membership (mounted-file mismatch MDL031, unmounted marker resolving elsewhere, duplicate braced MDL001)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T02:22:52Z"
updated = "2026-11-12T20:36:15Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/model.rs,crates/grimble-model/src/plan_check.rs,crates/grimble-model/tests/corpus/**", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/tests/corpus/**"]

[[acceptance]]
text = "A mounted file whose marker names a different system is MDL031"
bound = true

[[acceptance]]
text = "A second braced declaration of a system is MDL001"
bound = true
+++
