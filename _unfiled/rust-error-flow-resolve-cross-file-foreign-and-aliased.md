+++
id = "01M68YF34HSMN38Y5MXEDBM1EV"
title = "Rust error_flow: resolve cross-file, foreign and aliased Result error types"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T12:20:33Z"
updated = "2026-10-31T13:06:54Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/rust.rs", "crates/gob-symbols/src/types.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/src/lib.rs"]

[[acceptance]]
text = "Given fn returning Result<T, E> with E an enum declared in another file or a foreign non_exhaustive enum, when the linked model is folded, then rust_error_facts yields ClosedEnum or NonExhaustive with its variants; and a type alias Result<T> = Result<T, MyErr> resolves E"
bound = false
+++

Follow-up of ~YK88FQA: v1 resolves E only against enums in the same file; pub use / cross-file enums, foreign non_exhaustive enums and aliases are Unresolved. Also no pipeline consumer calls rust_error_facts yet.
