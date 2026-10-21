+++
id = "01M5ETB7SWJPH7EVK97WHEVEHY"
title = "GRL example runner: model inputs plus engine relations cell/owned_by (SYS001, CAP001)"
type = "task"
category = "in-progress"
priority = "low"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T08:48:17Z"
updated = "2026-10-21T22:54:33Z"
labels = ["area:grl"]
scope = ["crates/gob-plan/src/examples/**", "crates/gob-plan/src/exec/relations/**", "crates/gob-plan/src/exec/outcome/**", "crates/gob-plan/src/plan/ir.rs", "crates/grimble-check/src/example_model.rs", "crates/grimble-check/tests/example_model.rs", "changelog.d/01M5ETB7SWJPH7EVK97WHEVEHY.added.md", "crates/gob-plan/src/exec/core/mod.rs", "crates/gob-plan/src/exec/core/eval.rs", "crates/gob-plan/src/exec/core/rowkind.rs", "crates/gob-plan/src/examples/cells.rs", "crates/gob-plan/tests/examples_model.rs", "docs/design/grl-examples-model.md", "crates/gob-plan/Cargo.toml", "Cargo.lock", "crates/gob-plan/tests/ten_rules/cases/CAP001.grl"]

[[acceptance]]
text = "A GRL example may carry a model input and a rule using node or owned by runs against its nodes and owns selectors"
bound = true

[[acceptance]]
text = "A rule using node, cell or owned by on an example without a model is refused, and an unparsable model or bad owns glob is an error"
bound = true

[[acceptance]]
text = "cell rows report observed, granted and excused atoms per owning node, with nested grants covering descendants and unowned files yielding none"
bound = true

[[acceptance]]
text = "The SYS001 and CAP001 ten-rules examples pass"
bound = true
+++

Found while working ~ACSP6CZ. runner.rs returns Unsupported("model") for InputKind::Model, and the executor lacks the engine relations cell, owned_by (and unit-inside-artifact over a model). Needed to make SYS001 and CAP001 examples in crates/gob-plan/tests/ten_rules pass; then delete their KNOWN_ENGINE_GAPS entries.
