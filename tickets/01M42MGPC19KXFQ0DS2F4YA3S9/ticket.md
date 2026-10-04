+++
id = "01M42MGPC19KXFQ0DS2F4YA3S9"
title = "Land ratchet is count-blind: a second identical finding hides behind a pre-existing one"
type = "bug"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T04:59:50Z"
updated = "2026-10-04T04:59:50Z"
scope = ["crates/frob-land/src/ratchet.rs"]

[[acceptance]]
text = "Given the base has one finding X and the ticket adds a second X, when land runs, then it refuses naming the new occurrence"
bound = false
+++

Found by reading ratchet.rs: base and head are compared by fingerprint set, so a new duplicate occurrence is not new. Compare multiplicities; also key the base cache by engine and config (P-07). Evidence and repro: notes/review/v1-gap/D-incidents.md (P-06, P-07).
