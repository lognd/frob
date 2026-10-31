+++
id = "01M6812DDVSJ26J6SH1FGKJCXP"
title = "Land fast path: reuse the ticket-tier check result when the base moved only outside the ticket cone, so a land re-check is a memo hit"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-31T03:46:49Z"
updated = "2026-10-31T04:45:22Z"
idempotency_key = "land-fast-1"
scope = ["crates/frob-land/src/**", "crates/gob-check/src/tools.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/src/packages.rs"]

[[acceptance]]
text = "A land whose merged tree differs from the ticket-checked tree only in files outside the affected cone reuses the bound check result and runs no cargo stage"
bound = false

[[acceptance]]
text = "Test: a base move touching an unrelated crate does not rerun clippy or fmt on land"
bound = false
+++

Goal: land under one minute in the common disjoint case. The memo key already hashes stage inputs; land must key on the cone, not the whole tree.
