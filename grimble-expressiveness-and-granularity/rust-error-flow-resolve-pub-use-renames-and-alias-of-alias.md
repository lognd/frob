+++
id = "01M691R2Z1MMS5M4NVR42SZBGD"
title = "Rust error_flow: resolve pub use renames and alias-of-alias"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T13:17:53Z"
updated = "2026-11-06T02:16:56Z"
idempotency_key = "edbm1ev-fu1"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/rust.rs", "crates/gob-symbols/src/pipeline.rs"]

[[acceptance]]
text = "Given pub use X as Y and type R2<T> = R<T>, when error facts are linked, then E resolves through them"
bound = true
+++

Follow-up of ~EDBM1EV; external-crate enums stay Unresolved by design.
