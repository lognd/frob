+++
id = "01M44P4SY2DK41TS91PAAZFNR5"
title = "cycle state depends on wall-clock time near midnight UTC (planned vs active); tests flake"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-05T00:06:46Z"
updated = "2026-10-05T00:11:24Z"

[[acceptance]]
text = "Given a clock at 00:06 UTC and a zone still on the previous day, when a cycle is created with the default start, then its state is the documented one and matches at any other time of day"
bound = false

[[acceptance]]
text = "Given the cycle CLI tests, when they run at any wall-clock time, then their results do not change"
bound = true
+++

GitHub CI on f9d9c5d82 (windows-latest, run at 2026-10-05T00:06Z, which is still 2026-10-04 in the owner's local zone) failed two frob-cli cycle tests: new_takes_its_end_from_cycle_days_and_a_repeat_is_already (crates/frob/tests/cycle.rs:193) and close_is_refused_while_a_member_is_in_progress_with_a_live_lease (cycle.rs:272), both asserting a new cycle's state is "planned" but getting "active". The same tests pass at other times of day, so a cycle's start/state depends on wall-clock time and very likely mixes a local-zone date with a UTC date around midnight. Fix structurally: decide and document the zone cycle dates are evaluated in (docs/design/pm-enforcement.md or tickets.md), compute the default start and the planned/active/closed state from one injected clock and that zone everywhere, and make the CLI tests pin the clock (an env or config override already used by other time-dependent tests, or a new one) so they cannot depend on when CI runs. Add a test at the boundary: a run at 00:06 UTC when the configured zone is still the previous day.
