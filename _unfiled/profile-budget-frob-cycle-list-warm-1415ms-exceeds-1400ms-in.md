+++
id = "01M7HW0BKQV9MFTYSHJDZR00K1"
title = "Profile budget: frob cycle list warm 1415ms exceeds 1400ms in CI"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-16T09:46:25Z"
updated = "2026-11-16T09:46:25Z"
idempotency_key = "profile-cycle-list-1415"
labels = ["no-story"]
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "The cycle list budget in profile.toml is raised with a recorded reason so the CI profile job passes"
bound = false
+++

no-story: CI profile breach on experimental af4f91eac0 (1415 ms vs 1400 ms); ledger growth made cycle list slower. Budget calibration chore.
