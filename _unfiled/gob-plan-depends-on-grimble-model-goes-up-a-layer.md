+++
id = "01M5FRCMBS9DHQ223JWGN6RNW7"
title = "gob-plan depends on grimble-model (goes up a layer)"
type = "bug"
category = "in-progress"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-21T17:33:20Z"
updated = "2026-10-21T18:16:37Z"
scope = ["crates/gob-plan/src/examples/side.rs", "crates/gob-plan/src/examples/mod.rs", "crates/gob-plan/src/examples/model_reader.rs", "crates/gob-plan/Cargo.toml", "crates/grimble-check/src/lib.rs"]

[[acceptance]]
text = "Behaviour implemented and covered by a bound test or check"
bound = false
+++

Found while working ~KCX28FW: gob-plan (layer 6) uses grimble_model in crates/gob-plan/src/examples/side.rs; move that code or invert the dependency, then drop the ALLOWED row in crates/gob-dev/tests/layering.rs.
