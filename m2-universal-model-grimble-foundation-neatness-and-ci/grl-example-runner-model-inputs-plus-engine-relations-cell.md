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
updated = "2026-10-21T22:28:54Z"
labels = ["area:grl"]
scope = ["crates/gob-plan/src/examples/**", "crates/gob-plan/src/exec/relations/**", "crates/gob-plan/src/exec/outcome/**"]
+++

Found while working ~ACSP6CZ. runner.rs returns Unsupported("model") for InputKind::Model, and the executor lacks the engine relations cell, owned_by (and unit-inside-artifact over a model). Needed to make SYS001 and CAP001 examples in crates/gob-plan/tests/ten_rules pass; then delete their KNOWN_ENGINE_GAPS entries.
