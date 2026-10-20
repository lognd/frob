+++
id = "01M4052RG3QVXW6CHTG8BNS7CD"
title = "Marker keyring: one signing key, verify-only older keys, gradual re-marking"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:35Z"
updated = "2026-10-12T21:43:17Z"
idempotency_key = "m2-mirror2-keyring"
labels = ["milestone:2", "area:mirror", "creates:crates/frob-mirror/Cargo.toml", "creates:crates/frob-mirror/src/lib.rs", "creates:Cargo.lock"]
scope = ["crates/frob-mirror/src/keyring.rs", "crates/frob-mirror/Cargo.toml", "crates/frob-mirror/src/lib.rs", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given a keyring with a verify-only old key, when a marker under it is verified, then it verifies, and a new marker is signed only with the current key"
bound = true

[[acceptance]]
text = "Given a key past its verify-only period, when a marker under it is verified, then it fails as unknown kid"
bound = true

[[acceptance]]
text = "Given a rotation, when planned, then re-marking is a list of budgeted operations spread over runs"
bound = true
+++

Implements mirror.md section 3.3 (Marker format, keyring).

A keyring with one signing key and older keys that verify only for a stated period; rotation re-marks issues gradually within the budget. Keys come from the credentials environment, never repository files.
