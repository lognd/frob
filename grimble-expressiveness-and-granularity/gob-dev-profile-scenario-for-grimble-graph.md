+++
id = "01M69CZMK9ME0C3JXDGXCB72NG"
title = "gob-dev: profile scenario for grimble graph"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T16:34:15Z"
updated = "2026-10-31T16:34:20Z"
idempotency_key = "profile-grimble-graph"
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "Given grimble graph is a leaf command, when gob-dev profile and frob-docgen profile_coverage run, then grimble graph has a scenario or skip reason and both pass"
bound = false
+++

CI run 41217592314 failed: leaf commands with no scenario and no skip reason in profile.toml: grimble graph (profile job and frob-docgen profile_coverage test). Add a scenario modeled on the grimble check scenario.
