+++
id = "01M3ZX80ASECE0HYHJPNWZ071A"
title = "PACK010: repository WASM binary must be reproduced from in-repository source"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:39Z"
updated = "2026-10-03T03:34:39Z"
idempotency_key = "m2-sec-pack-reproducible"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-packs/src/reproduce.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7SMJ1W3K92Z6J59CYGQT"

[[acceptance]]
text = "Given a pack whose binary does not match a rebuild of its source, when verified, then PACK010 is emitted as an Error"
bound = false

[[acceptance]]
text = "Given a matching rebuild, when verified, then no finding is emitted"
bound = false
+++

Implements security.md section 2.8.

packs verify --rebuild rebuilds and compares; CI runs it when a pack changes; downgrading PACK010 is a GATE001 weakening.
