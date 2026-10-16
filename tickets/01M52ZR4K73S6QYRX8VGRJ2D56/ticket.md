+++
id = "01M52ZR4K73S6QYRX8VGRJ2D56"
title = "CI red on both OS: layering gob-check->gob-packs goes up a layer; dev-artifacts must need cone-compare job"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T18:31:50Z"
updated = "2026-10-16T19:14:20Z"
scope = ["crates/gob-dev/tests/layering.rs", ".github/workflows/**", "crates/frob-release/tests/**", "crates/gob-check/**", "crates/gob-packs/**", "changelog.d/**", "docs/**"]

[[acceptance]]
text = "gob-dev layering test and frob-release dev_workflow test pass"
bound = true
+++
