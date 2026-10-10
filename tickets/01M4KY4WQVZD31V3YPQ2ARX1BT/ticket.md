+++
id = "01M4KY4WQVZD31V3YPQ2ARX1BT"
title = "gob-check: rustdoc link to a private item breaks the Docs CI step"
type = "bug"
category = "todo"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-10T22:15:14Z"
updated = "2026-10-10T22:15:14Z"
scope = ["crates/gob-check/src/status.rs"]

[[acceptance]]
text = "cargo doc --no-deps -p gob-check with RUSTDOCFLAGS=-D warnings exits 0"
bound = false
+++

unresolved_finding_at docs link to private unresolved_finding_for (commit 11b4607c1)
