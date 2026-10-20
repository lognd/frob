+++
id = "01M38BCNNPR12GEC313XX7ST8X"
title = "land --drain: re-exec between lands when frob's own source changed"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5814"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/tickets/_land_queue.py", "tests/unit/test_land_queue.py", "docs/modules/tickets-landing.md"]
+++

`frob ticket land --drain` runs every queued entry in ONE python
process. With 40+ entries queued it never exits, so engine fixes that
LAND during the drain (today: T-5518, T-5522, T-5785, T-5813)
do not take effect until someone kills and restarts it, and a kill mid-
land is unsafe. Fix: at the top of each drain iteration, between lands,
compare the mtime/tree hash of frob's own installed source (the
`frob` package directory plus the native extensions) against the value
captured at process start; on change, log it and `os.execv` the same
argv so the next land runs the new code (leases, queue file and
land.lock are all durable, so a between-lands re-exec loses nothing).
Positive control: touch a frob source file during a drain of two
entries; the second entry's land log must show the new process pid.
Tiered-safety: automatic, logged.
