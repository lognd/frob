+++
id = "01M4052WS0WETQ6V4FZ9XENZPA"
title = "Property tests: duplicates (S3, L4, the lost and late create cases)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:40Z"
updated = "2026-10-03T05:51:40Z"
idempotency_key = "m2-mirror2-prop-dups"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/tests/prop_dups.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052W6Q1FAQK362YF6RCGW1"

[[links]]
kind = "blocked-by"
target = "01M4052WAB3H52W92NYG3AS571"

[[acceptance]]
text = "Given a lost create response and a crash, when the next run recovers, then exactly one issue exists for the ticket"
bound = false

[[acceptance]]
text = "Given a delayed create that lands after the retry, when the next run lists, then the extra issue is closed as a duplicate and its edits are captured"
bound = false

[[acceptance]]
text = "Given a human editing a marker in a later revision, when a run looks up the ticket, then no second issue is created (F4)"
bound = false
+++

Implements mirror.md section 3.7 (duplicate row) and the model README rows D0, F4, F5, F6.

With lost creates and no late deliveries, never two issues for one ticket; with a delayed create landing after the retry, at most one extra issue per uncertain create and the next run closes it and still reads its history.
