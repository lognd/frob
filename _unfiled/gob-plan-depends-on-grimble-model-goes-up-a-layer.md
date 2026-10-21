+++
id = "01M5FRCMBS9DHQ223JWGN6RNW7"
title = "gob-plan depends on grimble-model (goes up a layer)"
type = "bug"
category = "done"
outcome = "done"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-21T17:33:20Z"
updated = "2026-10-21T18:37:26Z"
scope = ["crates/gob-plan/src/examples/side.rs", "crates/gob-plan/src/examples/mod.rs", "crates/gob-plan/src/examples/model_reader.rs", "crates/gob-plan/Cargo.toml", "crates/grimble-check/src/lib.rs", "crates/grimble-check/src/example_model.rs", "crates/grimble-check/tests/example_model.rs", "crates/grimble/src/main.rs", "crates/gob-dev/tests/layering.rs", "Cargo.lock", "changelog.d/01M5FRCMBS9DHQ223JWGN6RNW7.changed.md", "crates/gob-plan/src/examples/corpus_tests.rs"]

[[acceptance]]
text = "Behaviour implemented and covered by a bound test or check"
bound = true
+++

Found while working ~KCX28FW: gob-plan (layer 6) uses grimble_model in crates/gob-plan/src/examples/side.rs; move that code or invert the dependency, then drop the ALLOWED row in crates/gob-dev/tests/layering.rs.
