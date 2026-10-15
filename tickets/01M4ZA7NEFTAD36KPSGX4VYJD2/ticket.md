+++
id = "01M4ZA7NEFTAD36KPSGX4VYJD2"
title = "Unfulfilled clippy expectations on Windows target in test crates (gob-trust and siblings)"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
points = 2
reporter = "lognd"
created = "2026-10-15T08:18:06Z"
updated = "2026-10-15T09:58:36Z"
idempotency_key = "fix-win-expect-2"
scope = ["crates/gob-trust/tests/trust.rs"]

[[acceptance]]
text = "cargo clippy for the Windows target is clean for every crate with a unix-gated disallowed_methods expectation"
bound = true
+++

CI run 38702342767 fails clippy on both ubuntu (windows target) and windows: expectation unfulfilled at crates/gob-trust/tests/trust.rs:3. Same class as ~9AA532R. Fix by cfg_attr(unix, expect(...)) where the offending call is unix-gated; iterate with cargo clippy --target x86_64-pc-windows-gnu -p <crate> --all-targets per crate until clean; widen lease per file.
