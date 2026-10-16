+++
id = "01M50CN1ETGK88AQ6H6JQGAVD0"
title = "ci: gob-dev layering (gob-packs->gob-plan up a layer) and publish no-consumer test fail on main"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-15T18:19:36Z"
updated = "2026-10-15T18:45:59Z"
scope = ["crates/gob-packs/**", "crates/gob-dev/**", "docs/design/boundaries.md"]

[[acceptance]]
text = "gob-dev layering and publish no-consumer tests pass"
bound = true
+++

found while working ~1XR3FK6: commit b7e45b936 added gob-packs -> gob-plan (layer 4 -> 5); layering test fails, and publish::tests::crates_with_no_consumer... reports crunk-check depends on unpublished gob-packs.
