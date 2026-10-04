+++
id = "01M42MGNSY7N4NANEFNG7AXHR1"
title = "Closing a ticket blocked by an open ticket succeeds (no no_open_blockers guard)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T04:59:49Z"
updated = "2026-10-04T12:57:37Z"
scope = ["crates/frob-evidence/src/done.rs"]

[[acceptance]]
text = "Given a ticket blocked by an open ticket, when it is closed as done, then it refuses naming the blocker"
bound = true
+++

Reproduced; tickets.md names the guard (also slice A PT-3). Add no_open_blockers to the done guards for outcomes done and fixed. Evidence and repro: notes/review/v1-gap/D-incidents.md (probe list).
