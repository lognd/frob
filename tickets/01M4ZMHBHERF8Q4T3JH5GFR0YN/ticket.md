+++
id = "01M4ZMHBHERF8Q4T3JH5GFR0YN"
title = "Gate train_state crashed-driver test to Linux (pid_alive is conservative elsewhere)"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
points = 1
reporter = "lognd"
created = "2026-10-15T11:18:10Z"
updated = "2026-10-15T17:17:58Z"
idempotency_key = "trainstate-win-test"
scope = ["crates/frob-land/src/train_state.rs"]

[[acceptance]]
text = "crashed_driver_is_reported_stale_and_resumable only runs where pid_alive can report death; windows nextest passes"
bound = true
+++

CI run 38720065929 windows nextest: train_state::tests::crashed_driver_is_reported_stale_and_resumable asserts s.stale but lock::pid_alive returns true on non-linux. Add #[cfg(target_os = "linux")] to the test (or the stale half).
