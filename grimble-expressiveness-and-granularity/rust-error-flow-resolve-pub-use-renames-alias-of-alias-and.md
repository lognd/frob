+++
id = "01M691R2Z1MMS5M4NVR42SZBGD"
title = "Rust error_flow: resolve pub use renames, alias-of-alias and wire workspace_rust_error_facts into a check"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T13:17:53Z"
updated = "2026-10-31T13:17:53Z"
idempotency_key = "edbm1ev-fu1"
scope = ["crates/gob-symbols/src/rust.rs", "crates/gob-symbols/src/pipeline.rs"]

[[acceptance]]
text = "Given pub use X as Y and type R2<T> = R<T>, when error facts are linked, then E resolves through them"
bound = false

[[acceptance]]
text = "Given a workspace, when a check verb runs, then it calls workspace_rust_error_facts"
bound = false
+++

Follow-up of ~EDBM1EV; external-crate enums stay Unresolved by design.
