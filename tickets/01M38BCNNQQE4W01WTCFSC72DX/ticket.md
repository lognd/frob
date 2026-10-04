+++
id = "01M38BCNNQQE4W01WTCFSC72DX"
title = "ticket new --points is not persisted"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5815"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/tickets/_new_renumber.py", "tests/test_tickets_points.py", "docs/modules/tickets-data-storage.md"]
+++

`frob ticket new --points N` accepted the flag but the created ticket
carries `points: null` (measured 2026-09-24 filing the coord tree and the
tiers tree; every filer script had to follow with `frob ticket points`).
Fix: persist points at creation; positive control: new --points 3 then
show must print points 3.
