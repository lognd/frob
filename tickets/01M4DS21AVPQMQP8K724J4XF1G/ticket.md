+++
id = "01M4DS21AVPQMQP8K724J4XF1G"
title = "frob-worktree: concurrent_work_on_overlapping_tickets_grants_exactly_one fails under machine load"
type = "bug"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-08T12:50:47Z"
updated = "2026-10-08T12:50:47Z"
labels = ["area:frob"]
scope = ["crates/frob-worktree/tests/work.rs"]
+++

Found while working ~S0S9G93: frob test --base experimental failed this test once (1501 tests executed in parallel with other agents' builds); it passed on three isolated reruns and in the goway full-suite run. Likely a timing assumption in the racing threads; make the assertion deterministic (barrier, no sleeps) or widen the window.
