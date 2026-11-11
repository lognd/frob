+++
id = "01M5FEF9785BFG86935HYZ7H5P"
title = "Share the inline-case dir reader across parser inline tests"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T14:40:01Z"
updated = "2026-11-11T05:03:37Z"
scope = ["crates/gob-testsupport/**", "crates/crunk-spec/tests/inline.rs", "crates/crunk-spec/Cargo.toml", "crates/gob-plan/tests/inline.rs", "crates/gob-plan/Cargo.toml", "crates/gob-directives/tests/inline.rs", "crates/gob-directives/Cargo.toml", "crates/grimble-model/tests/inline.rs", "crates/grimble-model/Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "The four parser inline.rs tests read their cases through one shared gob-testsupport helper."
bound = true
+++

tests/inline.rs in gob-plan, grimble-model, gob-directives and crunk-spec duplicate the resources/inline dir reader; extract a shared helper. Found while working ~2GG2KXR.
