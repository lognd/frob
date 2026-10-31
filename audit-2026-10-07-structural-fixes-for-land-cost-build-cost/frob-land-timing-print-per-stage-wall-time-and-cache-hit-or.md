+++
id = "01M6812E685HR5RAYJ4WNXYKAT"
title = "frob land --timing: print per-stage wall time and cache hit or miss so the land cost is measurable"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-31T03:46:50Z"
updated = "2026-10-31T04:40:11Z"
idempotency_key = "land-fast-3"
scope = ["crates/frob-land/src/verb.rs"]

[[acceptance]]
text = "frob land --timing prints each check stage with seconds and memo hit or miss"
bound = true

[[acceptance]]
text = "Test: output lists every tool stage once"
bound = true
+++

Needed to prove the under-a-minute target and find the next bottleneck.
