+++
id = "01M3ZFT5KZBX5H4FBJTCX0T4TP"
title = "frob-check perf test fails under concurrent builds; make the budget a measured benchmark, not a unit test"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T23:39:54Z"
updated = "2026-10-03T01:54:23Z"
idempotency_key = "m2-perf-test-flaky"
labels = ["milestone:2"]
scope = ["crates/frob-check/**", "crates/gob-check/**", "crates/frob-ack/tests/**"]

[[acceptance]]
text = "Given a full-workspace test run under heavy CPU load, when the suite runs, then no test asserts wall-clock time and the bench still reports the warm-run budget"
bound = false
+++

warm_run_on_this_repository_is_under_two_seconds failed during a full-workspace run while another worktree compiled, and passed alone at 1.7 s. A wall-clock assertion in the unit suite is load-sensitive. Move the 2 s budget check to the criterion bench and PERF001 (per D30 and the [perf] knobs), keep a unit test that asserts the timing breakdown is produced, and record the measured warm time in the bench output.
