+++
id = "01M68WWDSQW88MYX5EVYK88FQA"
title = "Rust adapter: feed resolved Result error types into gob-ir error_flow facts"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T11:52:53Z"
updated = "2026-10-31T12:26:12Z"
labels = ["no-story", "grimble"]
scope = ["crates/gob-symbols/src/rust.rs", "crates/gob-symbols/src/types.rs", "crates/gob-symbols/src/lib.rs"]

[[acceptance]]
text = "Given a Rust fn returning Result<T, E> with E a closed enum in the model, when the adapter folds it, then ErrorFacts::rust receives a ClosedEnum with its variants; Box<dyn Error>, anyhow::Error, foreign non_exhaustive enums map to Erased/NonExhaustive/Unresolved"
bound = true
+++

Follow-up of ~589WNWE: the symbolic core is gob_ir::error_flow; the adapter wiring (type resolution to RustErrorType) is not done.
