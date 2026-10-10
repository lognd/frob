+++
id = "01M4KYH3CT4JRJ2V0HGVVFYE34"
title = "gob-dev: profile.toml has no scenario for frob ticket closeout, so cargo dev profile aborts in CI"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-10T22:21:54Z"
updated = "2026-10-10T22:23:03Z"
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "the profile_coverage test passes"
bound = true
+++

found while fixing red base CI: profile step aborts
