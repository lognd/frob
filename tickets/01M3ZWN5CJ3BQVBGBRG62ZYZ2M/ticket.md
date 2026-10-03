+++
id = "01M3ZWN5CJ3BQVBGBRG62ZYZ2M"
title = "gob-symbols: a Rust file outside any Cargo package gets only its own crate's candidates"
type = "bug"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T03:24:21Z"
updated = "2026-10-03T03:24:21Z"
idempotency_key = "m2-gobsym-orphan-file-candidates"
labels = ["milestone:2", "soundness"]
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "Given a Rust file outside any Cargo package that calls x.m() on an unknown receiver, when the graph is built, then every fitting m in every crate gets a May edge or the call is Unknown"
bound = false
+++

Follow-up of ~Z0XMZEG. A Rust file with no Cargo.toml above it is never ruled out by CrateDeps, yet an unknown-receiver call in it gets May edges only to its own crate's methods. Soundness requires widening its candidates to every crate's fitting methods (or reporting such calls Unknown). No file in this repository hits it today.
