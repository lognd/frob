+++
id = "01M42MGNM3BBXJ5G2TVX4HH43T"
title = "Concurrent ledger writes fail with E-LEDGER-CAS: retries have no backoff (10 of 24 concurrent ticket new failed)"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T04:59:49Z"
updated = "2026-10-04T12:26:36Z"
scope = ["crates/gob-git/src/ledger.rs", "crates/gob-git/tests/ledger.rs"]

[[acceptance]]
text = "Given 24 concurrent ticket new, when they run, then all succeed"
bound = true
+++

Reproduced with 24 concurrent ticket new. Retry the CAS with jittered backoff within a bounded budget. Evidence and repro: notes/review/v1-gap/D-incidents.md (probe list).
