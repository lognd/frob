+++
id = "01M6VX2NSCBWN9FQ2CFYZ29PVA"
title = "grimble status takes 24s and 4.8 GB RSS (was 232 ms): blocks the profile CI job"
type = "bug"
category = "in-progress"
priority = "critical"
class = "expedite"
reporter = "lognd"
created = "2026-11-07T21:01:52Z"
updated = "2026-11-07T21:18:15Z"
scope = ["crates/grimble/**", "crates/grimble-cli/**", "crates/grimble-bind/**", "crates/grimble-lints/**", "crates/gob-dev/profile.toml"]

[[acceptance]]
text = "given a repo with manual tests, when grimble status runs, then it lists them from the loaded model without a full bind and stays inside its 3000 ms profile budget"
bound = false
+++
