+++
id = "01M6VX2NSCBWN9FQ2CFYZ29PVA"
title = "grimble status takes 24s and 4.8 GB RSS (was 232 ms): blocks the profile CI job"
type = "bug"
category = "todo"
priority = "critical"
class = "expedite"
points = 3
reporter = "lognd"
created = "2026-11-07T21:01:52Z"
updated = "2026-11-12T12:36:39Z"
scope = ["crates/grimble/**", "crates/grimble-cli/**", "crates/grimble-bind/**", "crates/grimble-lints/**", "crates/gob-dev/profile.toml"]

[[acceptance]]
text = "given a repo with manual tests, when grimble status runs, then it lists them from the loaded model without a full bind and stays inside its 3000 ms profile budget"
bound = true
+++
