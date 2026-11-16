+++
id = "01M5V7400HHPFFVXFJFD52N2C4"
title = "Scoped capability grants (may ... at) are ignored"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-26T04:22:25Z"
updated = "2026-11-16T08:34:12Z"
scope = ["crates/gob-plan/src/examples/cells.rs", "crates/gob-plan/src/examples/model_reader.rs", "crates/grimble-check/src/example_model.rs", "crates/gob-plan/tests/it/examples_model.rs", "crates/grimble-check/tests/it/example_model.rs", "docs/design/shared/grl-spec.md", "crates/gob-plan/src/examples/mod.rs"]

[[acceptance]]
text = "a may ... at grant only grants cells inside its selector, with a test"
bound = true
+++

Found while working ~FKKYQ41. Scoped grants (may ATOM at SELECTOR) are ignored when computing granted cells; they should only grant within the selected symbols.
